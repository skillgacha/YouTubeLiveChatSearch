from datetime import datetime
#import numpy as np
import glob
import os
import pandas as pd
import re
import streamlit as st
#import matplotlib.pyplot as plt

#タイムスタンプを日付表示に
def ts_to_dt(ts):
    dt = datetime.fromtimestamp(int(int(ts)/1000000))
    return dt

#video_idとtimeから直リンクアドレスを生成
def to_links(df):
    seconds = 0
    time_strs = df["time"].split(':')
    if len(time_strs) == 2:
        seconds = int(time_strs[0])*60 + int(time_strs[1])
    if len(time_strs) == 3:
        seconds = int(time_strs[0])*3600 + int(time_strs[0])*60 + int(time_strs[1])
    if seconds < 0:
        seconds = 0

    video_url = f'https://www.youtube.com/watch?v={df["video_id"]}&t={str(seconds)}s'

    return f'<a target="_blank" href="{video_url}">{df["video_title"]}</a>'
    #return video_url

def add_highlight(text, search):
    highlight = text.replace(search, f'<mark>{search}</mark>')
    return highlight

def sel_price(price_str, price_range):
    price = int(re.sub(r"\D", "", price_str))
    range = re.findall(r"[-+]?\d*\.\d+|\d+", price_range.replace(',', ''))
    return int(range[0]) <= price <= int(range[1])

#ソースデータ読み込み
@st.cache
def load_data():
    #df = pd.read_csv(f'{os.path.dirname(__file__)}/hiroyuki_yt-livechat_data.csv', low_memory=False)
    data_list = []
    files = glob.glob(f"{os.path.dirname(__file__)}/livechat_data/UC0yQ2h4gQXmVUFWZSqlMVOA/*.csv")
    for file in files:
        data_list.append(pd.read_csv(file, low_memory=False))
        #print(file)
    df = pd.concat(data_list, axis=0)
    df = df.fillna({'authorbadge': '', 'purchaseAmount': ''}).sort_values('timestampUsec')

    return df

@st.cache
def load_date():
    today = datetime.today()
    return today

#タイトルテキストの描画
st.title('ひろゆきYoutube生配信のライブチャットデータ')
df = load_data()
today = datetime.today()

#期間選択用のスライダー
time_range = st.slider('日時の絞り込み',
                         min_value=datetime(2018, 3, 1),
                         max_value=load_date(),
                         value=(datetime(2020, 1, 31), load_date()),
                         format='YYYY-MM-DD',
                         )
st.write('検索範囲: ', str(time_range[0].date()), str(time_range[1].date()))
start_time = int(time_range[0].timestamp())
end_time = int(time_range[1].timestamp())

#コメント検索フォーム
search_text = st.text_input(label='コメント検索', value='こんにちは')

#ユーザー名検索フォーム
search_user = st.text_input(label='ユーザー検索', value='ひろゆき')

#チャットの種類選択フォーム
selected_item = st.radio('チャットタイプ', ['指定しない', 'ノーマルチャットのみ', 'スーパーチャットのみ'])

#期間絞り込み
df_result = df.query(f'{str(start_time*1000000)} <= timestampUsec < {str(end_time*1000000)}')
#コメント絞り込み
df_result = df_result[df_result['text'].str.contains(str(search_text), na=False)]
#ユーザー絞り込み
df_result = df_result[df_result['user'].str.contains(str(search_user), na=False)]

#スパチャ絞り込み
if selected_item == 'ノーマルチャットのみ':
    chat_type = 'NORMALCHAT'
    df_result = df_result[df_result['type'] == chat_type]
elif selected_item == 'スーパーチャットのみ':
    chat_type = 'SUPERCHAT'
    df_result = df_result[df_result['type'] == chat_type]
    superchat_sel = ['全て', '100 - 199円', '200 - 499円', '500 - 999円', '1,000 - 1,999円', '2,000 - 4,999円', '5,000 - 9,999円', '10,000 - 50,000円', '外貨']
    superchat = st.radio('金額', superchat_sel)
    st.write(superchat)
    if superchat == '外貨':
        df_result = df_result[~df_result['purchaseAmount'].str.contains('￥', na=False)]
    elif superchat != '全て':
        df_result = df_result[df_result['purchaseAmount'].str.contains('￥', na=False)]
        df_result = df_result[df_result['purchaseAmount'].apply(sel_price, price_range=superchat)]
    else:
        df_result = df_result[df_result['type'] == chat_type]

if len(df_result) > 2500:
    st.write('<span style="color:red;background:pink">条件を満たす対象が多すぎます。検索内容を絞り込んでください</span>',
              unsafe_allow_html=True)

else:
    #該当データがあればタイムスタンプ列を見やすく変換
    if len(df_result) > 0:
        df_result["timestampUsec"] = df_result["timestampUsec"].apply(ts_to_dt)
        #video_idをハイパーリンクに
        df_result["video_title"] = df_result.apply(to_links, axis=1)

        if len(search_text) > 0:
            df_result['text'] = df_result['text'].apply(add_highlight, search=search_text)
        if len(search_user) > 0:
            df_result['user'] = df_result['user'].apply(add_highlight, search=search_user)

    #件数表示
    if len(df_result) > 0:
        st.write(f'{len(df_result)}件のコメントが該当しました')
    else:
        st.write('条件に一致するコメントはありませんでした')

    #表の描画
    #st.dataframe(df_result)
    df_result.set_axis(['チャットコメント','user','authorbadge','タイトル','time','type','スパチャ金額','投稿日時','video_id','Chat_No'], axis=1, inplace=True)

    #データフレーム表示だとハイパーリンクが機能しないのでテーブルで表示
    df_width = '50px'
    df_result = df_result[['チャットコメント','user','タイトル','time','スパチャ金額','投稿日時','authorbadge','video_id']].to_html(escape=False, col_space=['400px', '150px','300px', df_width, df_width, '200px', df_width, df_width], index=False)

    st.write(df_result, unsafe_allow_html=True)
