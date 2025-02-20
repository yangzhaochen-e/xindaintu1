import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from io import BytesIO
import numpy as np
import os

# 电流调节策略
def determine_current(voltage, freq, duration):
    if (freq > 20 and voltage > 200 and duration > 10) or (freq > 50 and duration > 10) or (freq > 70 and voltage > 200):
        return 2.0
    elif 100 <= voltage < 200:
        return 1.5
    elif 50 <= voltage < 100:
        return 1.0
    else:
        return 0.0


# 生成可视化图表
def create_eeg_plot(df):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 绘制脑电波形
    fig.add_trace(go.Scatter(
        x=df['时间（秒）'],
        y=df['电压（μV）'],
        mode='lines',
        name='EEG Signal',
        line=dict(color='#1f77b4')
    ), secondary_y=False)

    # 计算并绘制电流
    current_values = []
    for _, row in df.iterrows():
        current = determine_current(row['电压（μV）'], row['频率（Hz）'], row['持续时间（秒）'])
        current_values.append(current)
    df['电流（mA）'] = current_values

    fig.add_trace(go.Scatter(
        x=df['时间（秒）'],
        y=df['电流（mA）'],
        mode='lines',
        name='电流调节',
        line=dict(color='#ff7f0e')
    ), secondary_y=True)

    # 动态标注电流强度区域
    current_start = None
    for i, row in df.iterrows():
        current = row['电流（mA）']
        if current > 0:
            if current_start is None:
                current_start = row['时间（秒）']
        else:
            if current_start is not None:
                # 添加颜色区域
                fig.add_vrect(
                    x0=current_start,
                    x1=row['时间（秒）'],
                    fillcolor=get_current_color(max(df.loc[(df['时间（秒）'] >= current_start) & (df['时间（秒）'] < row['时间（秒）']), '电流（mA）'])),
                    opacity=0.2,
                    layer="below"
                )
                current_start = None

    # 设置图表样式
    fig.update_layout(
        title='实时脑电图与电流调节分析',
        xaxis_title='时间（秒）',
        yaxis_title='电压（μV）',
        yaxis2_title='电流（mA）',
        hovermode="x unified",
        height=600,
        annotations=[
            dict(
                x=0.5, y=-0.15,
                xref="paper", yref="paper",
                text="颜色说明：红色=2mA | 橙色=1.5mA | 黄色=1mA",
                showarrow=False
            )
        ]
    )
    return fig


def get_current_color(current):
    return {
        2.0: '#ff0000',  # 红色
        1.5: '#ffa500',  # 橙色
        1.0: '#ffff00'  # 黄色
    }.get(current, '#ffffff')


# 生成模拟数据
def generate_simulated_data():
    num_points = 21
    time_points = np.linspace(0, 2, num_points)
    voltage = np.random.randint(-250, 250, num_points)
    freq = np.random.randint(0, 100, num_points)
    duration = np.random.rand(num_points)
    data = {
        '时间（秒）': time_points,
        '电压（μV）': voltage,
        '频率（Hz）': freq,
        '持续时间（秒）': duration
    }
    return pd.DataFrame(data)
# 缓存读取文件操作
@st.cache_data
def read_reference_file():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, '新建 XLSX 工作表 (3).xlsx')
    try:
        df = pd.read_excel(file_path, sheet_name='Sheet1')
        return df
    except FileNotFoundError:
        st.error("参考示例文件未找到，请确保文件在项目目录中。")
        st.stop()

# Streamlit界面
st.title('癫痫治疗电流调节分析系统')
st.header('EEG数据上传与分析')
data_option = st.radio("选择数据来源", ("上传文件", "生成模拟数据"))
if data_option == "上传文件":
    uploaded_file = st.file_uploader("上传EEG数据文件（.xlsx）", type="xlsx")
    if uploaded_file:
        try:
            # 尝试读取文件
            bytes_data = uploaded_file.getvalue()
            df = pd.read_excel(BytesIO(bytes_data), sheet_name='Sheet1')
            # 显示所需上传数据格式（这里展示数据的基本信息和前几行）
            st.subheader("所需上传数据格式说明")
            st.write("数据基本信息：")
            st.write(df.info())
            st.write("数据前几行内容：")
            st.dataframe(df.head())
            # 生成可视化
            st.subheader("脑电图与电流调节分析")
            fig = create_eeg_plot(df)
            st.plotly_chart(fig, use_container_width=True)
            # 显示调节策略说明
            st.markdown("""
            **电流调节策略说明：**
            - 🔴 2.0 mA：
                - 阵发性放电频率超过20Hz，幅度超过200µV，持续时间超过10秒；
                - 高频放电（超过50Hz）持续存在超过10秒，并未得到有效抑制；
                - 过度异常高频波（超过70Hz，幅度超过200µV）。
            - 🟠 1.5 mA：尖波幅度较大（大约100µV到200µV）。
            - 🟡 1.0 mA：较小尖波（幅度大约在50µV到100µV之间）。
            - ⚪ 0.0 mA：正常范围。
            """)
            # 添加下载按钮
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="下载分析结果",
                data=csv,
                file_name='eeg_analysis.csv',
                mime='text/csv'
            )
        except Exception as e:
            st.error(f"上传文件格式不正确，错误信息：{e}")
    else:
        # 当没有上传文件时，不显示结果分析
        st.info("请上传EEG数据文件以进行分析。")
else:
    # 生成模拟数据并显示结果
    simulated_df = generate_simulated_data()
    st.subheader("模拟数据预览")
    st.dataframe(simulated_df.head(10))
    st.subheader("脑电图与电流调节分析")
    fig = create_eeg_plot(simulated_df)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("""
    **电流调节策略说明：**
    - 🔴 2.0 mA：
        - 阵发性放电频率超过20Hz，幅度超过200µV，持续时间超过10秒；
        - 高频放电（超过50Hz）持续存在超过10秒，并未得到有效抑制；
        - 过度异常高频波（超过70Hz，幅度超过200µV）。
    - 🟠 1.5 mA：尖波幅度较大（大约100µV到200µV）。
    - 🟡 1.0 mA：较小尖波（幅度大约在50µV到100µV之间）。
    - ⚪ 0.0 mA：正常范围。
    """)
    csv = simulated_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="下载模拟分析结果",
        data=csv,
        file_name='simulated_eeg_analysis.csv',
        mime='text/csv'
    )