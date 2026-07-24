import json
import pandas as pd
import streamlit as st
import calendar
import plotly.express as px

st.set_page_config(page_title='Spotify Listening Stats', page_icon='🎸', layout='wide')
# Upload files
uploaded_files = st.file_uploader(
    'Upload your Spotify Streaming History JSON files — your data is not stored',
    type='json',
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("Download your extended streaming history from Spotify (Account → Privacy Settings), then upload all Streaming_History_Audio_*.json files above.")
    st.stop()

all_records = []
for f in uploaded_files:
    data = json.load(f)
    all_records.extend(data)

#################### Data Cleaning and Sorting ####################

# Create dataframe
df = pd.DataFrame(all_records)

# Rename long column names
df = df.rename(columns={
    'master_metadata_track_name': 'track',
    'master_metadata_album_artist_name': 'artist',
    'master_metadata_album_album_name': 'album',
    'ms_played': 'ms',
    'conn_country': 'country'
})

# Drop null tracks and filter out plays under 30 seconds (same as spotify)
df = df.dropna(subset=['track'])
df = df[df['ms'] >= 30000]

# Turns timestamp string into datetime and creates cooresponding columns
df['ts'] = pd.to_datetime(df['ts'])
df['year'] = df['ts'].dt.year
df['month'] = df['ts'].dt.month
df['hour'] = df['ts'].dt.hour
df['day_of_week'] = df['ts'].dt.day_of_week

# Makes it so artist will be displayed with track and album (for streamlit)
df['track_artist'] = df['track'] + ' — ' + df['artist']
df['album_artist'] = df['album'] + ' - ' + df['artist']

# Columns to include in dataframe
columns = [
    'ts', 'platform', 'ms', 'country',
    'track', 'artist', 'album', 'spotify_track_uri',
    'track_artist', 'album_artist', 'reason_start', 
    'reason_end', 'shuffle', 'skipped', 'offline', 
    'year', 'month','hour', 'day_of_week'
]
df = df[columns]

# Define and apply platform cleaning to df during data cleaning (before sidebar)
def clean_platform(platform):
    if pd.isna(platform):
        return 'Unknown'
    platform = platform.lower()
    if 'ios' in platform or 'iphone' in platform or 'ipad' in platform:
        return 'iOS'
    if 'android' in platform:
        return 'Android'
    if 'windows' in platform:
        return 'Windows'
    if 'mac' in platform or 'os x' in platform or 'osx' in platform:
        return 'Mac'
    if 'web' in platform or 'chrome' in platform:
        return 'Web'
    if 'xbox' in platform or 'playstation' in platform or 'ps4' in platform or 'ps5' in platform:
        return 'Console'
    return 'Other'

df['platform'] = df['platform'].apply(clean_platform)

# Sidebar filters
st.sidebar.title('Filters')
years = ['All Time'] + sorted(df['year'].unique().tolist())
selected_year = st.sidebar.selectbox('Select Year', years)
platforms = ['All'] + sorted(df['platform'].unique().tolist())
selected_platform = st.sidebar.selectbox('Platform', platforms)
selected_shuffle = st.sidebar.selectbox('Shuffle', ['All', 'Shuffle On', 'Shuffle Off'])
selected_offline = st.sidebar.selectbox('Offline', ['All', 'Offline Only', 'Online Only'])
st.sidebar.markdown('---')
st.sidebar.markdown('Built by [Derek Mahoney](https://github.com/derekmahoney2)')
st.sidebar.caption('Your data is processed in your browser session and is not stored or shared. Upload at your own discretion.')

# Apply filters
filtered_df = df.copy()
if selected_year != 'All Time':
    filtered_df = filtered_df[filtered_df['year'] == selected_year]
if selected_platform != 'All':
    filtered_df = filtered_df[filtered_df['platform'] == selected_platform]
if selected_shuffle == 'Shuffle On':
    filtered_df = filtered_df[filtered_df['shuffle'] == True]
elif selected_shuffle == 'Shuffle Off':
    filtered_df = filtered_df[filtered_df['shuffle'] == False]
if selected_offline == 'Offline Only':
    filtered_df = filtered_df[filtered_df['offline'] == True]
elif selected_offline == 'Online Only':
    filtered_df = filtered_df[filtered_df['offline'] == False]

#################### Data Analysis ####################

# Top streamed artists
top_artist_streams = filtered_df['artist'].value_counts().head(10)

# Top streamed albums
top_albums = filtered_df['album_artist'].value_counts().head(10)

# Listening habits
# Total listening time for each hour
hourly_listening = (filtered_df.groupby('hour')['ms'].sum() / 60000).round()
hourly_listening = hourly_listening.reindex(range(24), fill_value=0)

# Table: ranked by most listening time
top_hours = hourly_listening.sort_values(ascending=False).head(10)
top_hours.index = [
    f"{(h % 12) or 12} {'AM' if h < 12 else 'PM'}"
    for h in top_hours.index
]
top_hours.index.name = 'Time'
listening_by_hour = hourly_listening.sort_index()

listening_by_hour.index = [
    f"{(h % 12) or 12} {'AM' if h < 12 else 'PM'}"
    for h in listening_by_hour.index
]
time_order = [
    '1 AM', '2 AM', '3 AM', '4 AM', '5 AM', '6 AM', 
    '7 AM', '8 AM', '9 AM', '10 AM', '11 AM', '12 PM', 
    '1 PM', '2 PM', '3 PM', '4 PM', '5 PM', '6 PM', 
    '7 PM', '8 PM', '9 PM', '10 PM', '11 PM', '12 AM'
]
listening_by_hour.index = pd.CategoricalIndex(listening_by_hour.index, categories=time_order, ordered=True)

# Top streamed songs 
top_songs = filtered_df['track_artist'].value_counts().head(10)

# Skipped analysis
skipped_artists = filtered_df[filtered_df['skipped']]['artist'].value_counts().head(10)
skipped_songs = filtered_df[filtered_df['skipped']]['track_artist'].value_counts().head(10)

# Total minutes and by year
total_minutes = int((filtered_df['ms'].sum() / 60000).round())
unique_artists = filtered_df['artist'].nunique()

# Monthly
monthly_artist = filtered_df.groupby(['month', 'artist']).size().reset_index(name='count')
top_artist_by_month = monthly_artist.sort_values(['month', 'count'], ascending=[True, False]).groupby('month').head(1).reset_index(drop=True)
monthly_song = filtered_df.groupby(['month', 'track_artist']).size().reset_index(name='count')
top_song_by_month = monthly_song.sort_values(['month', 'count'], ascending=[True, False]).groupby('month').head(1).reset_index(drop=True)
# Adds the months for bar chart in streamlit
top_artist_by_month['month'] = top_artist_by_month['month'].apply(lambda x: calendar.month_name[x])
top_song_by_month['month'] = top_song_by_month['month'].apply(lambda x: calendar.month_name[x])

# Number of streams for each platform
platform_counts = filtered_df['platform'].value_counts()

#################### Streamlit ####################

st.title('My Spotify Stats 🎵')

col1, col2, col3 = st.columns(3)
with col1:
    st.metric('Total Minutes Listened', total_minutes, border=True)
with col2:
    st.metric('Total Streams', len(filtered_df), border=True)
with col3:
    st.metric('Unique Artists', unique_artists, border=True)


tab1, tab2, tab3, tab4 = st.tabs(
    ['Top Artists', 'Top Songs', 
     'Listening Habits', 'Skip Analysis'
     ])
with tab1:
    st.subheader('Top 10 Artists')
    st.dataframe(
        top_artist_streams, column_config={
            'artist': 'Artist',
            'count': 'Streams'
        })
    st.divider()
    st.subheader('Top Artist by Month')
    fig = px.bar(
        top_artist_by_month,
        x='month',
        y='count',
        color='artist',
        labels={'month': 'Month', 'count': 'Streams', 'artist': 'Artist'},
        category_orders={'month': list(calendar.month_name)[1:]}
    )
    st.plotly_chart(fig, use_container_width=True, key='artist_month_chart')
    st.divider()
with tab2:
    st.subheader('Top 10 Songs')
    st.dataframe(
        top_songs, column_config={
            'track_artist': 'Track',
            'count': 'Streams'
        })
    st.divider()
    st.subheader('Top Song by Month')
    fig = px.bar(
        top_song_by_month,
        x='month',
        y='count',
        color='track_artist',
        labels={'month': 'Month', 'count': 'Streams', 'artist': 'Artist', 'track_artist':'Song'},
        category_orders={'month': list(calendar.month_name)[1:]}
    )
    st.plotly_chart(fig, use_container_width=True, key='song_month_chart')
    st.divider()
    st.subheader('Top Albums')
    st.dataframe(
        top_albums, column_config={
            'album_artist': 'Album',
            'count': 'Streams by Album'
        })
    st.divider()
with tab3:
    st.subheader('Top 10 Hours')
    st.dataframe(
        top_hours, column_config={
        'ms': 'Minutes Streamed'
    })
    st.divider()
    st.subheader('Listening Habits by Hour')
    st.bar_chart(listening_by_hour, x_label='Hour', y_label='Minutes', color=(0,255,0))
    st.divider()
    st.subheader('Streaming by Platform')
    fig = px.pie(
        values=platform_counts.values,
        names=platform_counts.index,
        labels={'names': 'Platform', 'values': 'Streams'}
    )
    fig.update_layout(legend_title_text='Platform')
    st.plotly_chart(fig, use_container_width=True, key='platform_chart')
    st.divider()
with tab4:
    st.subheader('Most Skipped Artists')
    st.dataframe(
        skipped_artists, column_config={
            'artist': 'Artist',
            'count': 'Skips'
        })
    st.divider()
    st.subheader('Most Skipped Songs')
    st.dataframe(
        skipped_songs, column_config={
            'track_artist': 'Song',
            'count': 'Skips'
        })
    st.divider()
