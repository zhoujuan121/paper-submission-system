import streamlit as st
import pandas as pd
import datetime
import hashlib
import os
import json

# 页面配置 - 必须放在最前面！
st.set_page_config(
    page_title="论文投稿备案系统",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# 隐藏整个菜单
hide_menu_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    </style>
"""
st.markdown(hide_menu_style, unsafe_allow_html=True)


# ==================== 数据持久化函数 ====================
def save_submissions():
    """保存备案数据到本地文件"""
    try:
        with open('submissions_data.json', 'w', encoding='utf-8') as f:
            json.dump(st.session_state.submissions, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"保存数据失败: {e}")


def load_submissions():
    """从本地文件加载备案数据"""
    try:
        with open('submissions_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []  # 文件不存在时返回空列表
    except Exception as e:
        st.error(f"加载数据失败: {e}")
        return []


# ==================== 安全配置函数 ====================
def get_security_config():
    """安全地获取系统配置"""
    try:
        return {
            'admin_password': st.secrets["app"]["admin_password"],
            'max_login_attempts': st.secrets["security"].get("max_login_attempts", 3),
            'debug_mode': st.secrets["app"].get("debug_mode", False)
        }
    except:
        st.warning("⚠️ 未找到secrets.toml文件，使用默认开发配置")
        return {
            'admin_password': "keyanban123456",
            'max_login_attempts': 5,
            'debug_mode': True
        }


# ==================== 数据初始化 ====================
def init_session_state():
    """初始化会话状态"""
    if 'user_role' not in st.session_state:
        st.session_state.user_role = "科研人员"
    if 'is_authenticated' not in st.session_state:
        st.session_state.is_authenticated = False
    if 'submissions' not in st.session_state:
        st.session_state.submissions = load_submissions()
    if 'warning_journals' not in st.session_state:
        init_warning_journals()
    if 'show_admin_login' not in st.session_state:
        st.session_state.show_admin_login = False
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None
    if 'user_id' not in st.session_state:  # 新增：用户唯一标识
        st.session_state.user_id = str(datetime.datetime.now().timestamp())  # 时间戳作为临时ID


def init_warning_journals():
    """初始化预警期刊数据"""
    try:
        # 尝试读取CSV文件
        df = pd.read_csv('warning_journals_20251117.csv')
        df_cleaned = clean_dataframe(df)
        st.session_state.warning_journals = df_cleaned
    except FileNotFoundError:
        # 如果文件不存在，创建示例数据
        st.session_state.warning_journals = create_sample_journals()


def clean_dataframe(df):
    """清理数据框"""
    df_cleaned = df.dropna(axis=1, how='all')
    unnamed_cols = [col for col in df_cleaned.columns if 'Unnamed' in col]
    if unnamed_cols:
        df_cleaned = df_cleaned.drop(columns=unnamed_cols)
    return df_cleaned


def create_sample_journals():
    """创建示例预警期刊数据"""
    sample_data = {
        '期刊名称': [
            'Bioengineered', 'European Review for Medical and Pharmacological Sciences',
            'OncoTargets and Therapy', 'Medical Science Monitor'
        ],
        '预警年份': [2023, 2022, 2021, 2020],
        '预警来源': ['中科院预警', '中科院预警', '中科院预警', '中科院预警']
    }
    return pd.DataFrame(sample_data)


# ==================== 登录系统 ====================
def login_system():
    """登录系统界面"""
    with st.sidebar:
        st.header("🔐 系统登录")
        st.info("科研人员无需密码，直接使用功能")

        # 显示当前身份
        if st.session_state.user_role == "科研办审核员":
            st.success("✅ 当前身份：科研办审核员")
            if st.button("🔁 切换至科研人员身份"):
                st.session_state.user_role = "科研人员"
                st.session_state.is_authenticated = True
                st.session_state.current_user = "科研人员"
                # 重新生成用户ID，确保数据隔离
                st.session_state.user_id = str(datetime.datetime.now().timestamp())
                st.experimental_rerun()
        else:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚀 科研人员登录", use_container_width=True, type="primary"):
                    st.session_state.user_role = "科研人员"
                    st.session_state.is_authenticated = True
                    st.session_state.current_user = "科研人员"
                    # 重新生成用户ID，确保数据隔离
                    st.session_state.user_id = str(datetime.datetime.now().timestamp())
                    st.success("✅ 以科研人员身份登录")
                    st.experimental_rerun()

            with col2:
                if st.button("🔐 管理员登录", use_container_width=True):
                    st.session_state.show_admin_login = True

            # 管理员登录表单
            if st.session_state.show_admin_login:
                st.markdown("---")
                st.subheader("管理员登录")

                password = st.text_input(
                    "请输入管理员密码",
                    type="password",
                    placeholder="输入管理员密码"
                )

                if st.button("✅ 验证身份"):
                    handle_admin_login(password)

                if st.button("❌ 取消"):
                    st.session_state.show_admin_login = False
                    st.experimental_rerun()


def handle_admin_login(password):
    """处理管理员登录"""
    security_config = get_security_config()
    correct_password = security_config['admin_password']

    if password == correct_password:
        st.session_state.user_role = "科研办审核员"
        st.session_state.is_authenticated = True
        st.session_state.current_user = "科研办管理员"
        st.session_state.show_admin_login = False
        st.success("✅ 管理员身份验证成功！")
        st.experimental_rerun()
    else:
        st.error("❌ 密码错误，请重新输入")


# ==================== 管理功能 ====================
def management_functions():
    """管理功能界面"""
    with st.sidebar:
        st.markdown("---")
        st.header("🔧 管理功能")

        # 预警期刊数据上传 - 仅科研办审核员可见
        if st.session_state.user_role == "科研办审核员":
            st.subheader("更新预警期刊库")
            uploaded_file = st.file_uploader("上传预警期刊列表(CSV)", type=['csv'])

            if uploaded_file is not None:
                try:
                    df = pd.read_csv(uploaded_file)
                    df_cleaned = clean_dataframe(df)
                    st.session_state.warning_journals = df_cleaned
                    st.success(f"✅ 成功更新预警期刊库！共 {len(df_cleaned)} 条记录。")
                except Exception as e:
                    st.error(f"❌ 文件读取错误: {e}")
        else:
            st.subheader("更新预警期刊库")
            st.info("🔒 此功能仅限科研办审核员使用")

        # 显示统计信息
        st.markdown("---")
        st.subheader("📊 系统统计")
        st.write(f"预警期刊数量: **{len(st.session_state.warning_journals)}** 种")

        # 根据用户角色显示不同的备案数量
        if st.session_state.user_role == "科研办审核员":
            # 审核员看到总备案数
            total_count = len(st.session_state.submissions)
            st.write(f"总备案数量: **{total_count}** 条")
        else:
            # 科研人员只看到自己的备案数
            my_count = len([s for s in st.session_state.submissions if s.get('提交用户ID') == st.session_state.user_id])
            st.write(f"我的备案数量: **{my_count}** 条")

        # 审核统计（仅科研办可见）
        if st.session_state.user_role == "科研办审核员" and st.session_state.submissions:
            records_df = pd.DataFrame(st.session_state.submissions)
            pending_count = len(records_df[records_df['状态'] == '待审核'])
            approved_count = len(records_df[records_df['状态'] == '审核通过'])
            rejected_count = len(records_df[records_df['状态'] == '审核驳回'])

            st.write(f"待审核: **{pending_count}** 条")
            st.write(f"已通过: **{approved_count}** 条")
            st.write(f"已驳回: **{rejected_count}** 条")


# ==================== 主应用功能 ====================
def main_application():
    """主应用界面"""
    # 应用标题和描述
    st.title("📚 论文投稿备案与期刊预警系统")

    # 根据用户角色显示不同的界面
    if not st.session_state.is_authenticated:
        show_welcome_page()
    elif st.session_state.user_role == "科研人员":
        show_researcher_interface()
    else:
        show_admin_interface()


def show_welcome_page():
    """显示欢迎页面"""
    st.markdown("---")
    st.info("🚀 系统已就绪，请使用左侧菜单开始操作")

    # 显示系统状态
    col1, col2 = st.columns(2)
    with col1:
        st.metric("预警期刊", len(st.session_state.warning_journals))
    with col2:
        st.metric("总备案记录", len(st.session_state.submissions))


def show_researcher_interface():
    """科研人员界面"""
    tab1, tab2, tab3 = st.tabs(["📝 投稿备案", "📋 我的备案记录", "🔍 预警期刊查询"])

    with tab1:
        show_submission_interface()

    with tab2:
        show_my_submissions()

    with tab3:
        show_journal_search_interface()


def show_my_submissions():
    """显示当前用户的备案记录"""
    st.header("我的备案记录")

    # 过滤出当前用户的记录
    user_submissions = [s for s in st.session_state.submissions if s.get('提交用户ID') == st.session_state.user_id]

    if not user_submissions:
        st.info("您还没有提交过备案记录")
        return

    st.write(f"您共有 **{len(user_submissions)}** 条备案记录：")

    # 转换为DataFrame显示，隐藏用户ID字段
    display_data = []
    for submission in user_submissions:
        display_item = {k: v for k, v in submission.items() if k not in ['提交用户ID', '提交用户角色']}
        display_data.append(display_item)

    df = pd.DataFrame(display_data)

    # 添加状态筛选
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox("按状态筛选", ["全部", "审核通过", "审核驳回"])
    with col2:
        warning_filter = st.selectbox("按预警状态", ["全部", "安全", "历年预警期刊"])

    # 应用筛选
    filtered_df = df.copy()
    if status_filter != "全部":
        filtered_df = filtered_df[filtered_df['状态'] == status_filter]
    if warning_filter != "全部":
        filtered_df = filtered_df[filtered_df['预警状态'] == warning_filter]

    st.write(f"显示 **{len(filtered_df)}** 条记录：")
    st.dataframe(filtered_df, use_container_width=True)

    # 导出功能
    if len(filtered_df) > 0:
        csv = filtered_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="📥 导出我的备案记录",
            data=csv,
            file_name=f"我的备案记录_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            mime='text/csv',
        )


def show_submission_interface():
    """投稿备案界面"""
    st.header("论文投稿备案")

    with st.form("submission_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            paper_title = st.text_input("论文标题*", placeholder="请输入完整的论文标题")
            authors = st.text_area("第一作者*", placeholder="第一作者姓名")
            corresponding_author = st.text_input("通讯作者*", placeholder="通讯作者姓名")
            department = st.selectbox("所属科室*", [
                "心内科", "心外科", "超声科", "放射科", "体外循环科",
                "麻醉科", "检验科", "输血科", "心功能科", '护理', '其他'
            ])

        with col2:
            target_journal = st.text_input("目标期刊名称*", placeholder="请输入完整的期刊名称")
            planned_submission_date = st.date_input("拟投稿日期", datetime.date.today())

        st.markdown("**注意**: 带 * 的字段为必填项")
        submitted = st.form_submit_button("🚀 提交备案申请")

        if submitted:
            handle_submission(paper_title, authors, corresponding_author,
                              department, target_journal, planned_submission_date)


def handle_submission(paper_title, authors, corresponding_author, department, target_journal, planned_submission_date):
    """处理投稿备案"""
    # 基本验证
    if not all([paper_title, authors, corresponding_author, department, target_journal]):
        st.error("❌ 请填写所有必填字段！")
        return

    # 检查期刊是否在预警列表中
    journal_match = st.session_state.warning_journals[
        st.session_state.warning_journals['期刊名称'].str.lower() == target_journal.lower()
        ]

    # 生成备案ID
    record_id = f"BA{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

    submission_data = {
        '备案ID': record_id,
        '论文标题': paper_title,
        '第一作者': authors,
        '目标期刊': target_journal,
        '通讯作者': corresponding_author,
        '所属科室': department,
        '提交时间': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        '预警状态': '历年预警期刊' if not journal_match.empty else '安全',
        '提交用户ID': st.session_state.user_id,  # 记录提交者
        '提交用户角色': st.session_state.user_role  # 记录用户角色
    }

    if not journal_match.empty:
        st.error("⚠️ **预警提醒**")
        st.write(f"您选择的期刊 **'{target_journal}'** 在以下预警列表中：")
        st.dataframe(journal_match, use_container_width=True)
        st.error("❌ **您的备案申请已被驳回**")
        st.warning("**重要提示**: 在此期刊上发表论文将无法报销并奖励，请改投其他期刊。")

        submission_data['状态'] = '审核驳回'
        submission_data['审核意见'] = '历年预警期刊，不予报销奖励，请改投其他期刊'
        submission_data['审核人'] = '科研办'
        submission_data['审核时间'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    else:
        st.success("✅ **期刊校验通过，备案已自动完成！**")
        submission_data['状态'] = '审核通过'
        submission_data['审核意见'] = '无预警，自动通过，可投稿'
        submission_data['审核人'] = '科研办'
        submission_data['审核时间'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 保存提交记录
    st.session_state.submissions.append(submission_data)
    save_submissions()  # 立即保存到文件

    # 显示提交摘要
    st.markdown("---")
    st.subheader("备案信息摘要")
    summary_data = {k: v for k, v in submission_data.items() if k not in ['提交用户ID', '提交用户角色']}
    summary_df = pd.DataFrame([summary_data])
    st.dataframe(summary_df, use_container_width=True)


def show_journal_search_interface():
    """期刊查询界面"""
    st.header("预警期刊查询")

    # 搜索功能
    col1, col2 = st.columns([2, 1])

    with col1:
        search_term = st.text_input("🔍 搜索期刊名称", placeholder="输入期刊名称关键词")

    with col2:
        search_type = st.selectbox("查询方式", ["精确查询"])

    # 筛选数据
    display_df = st.session_state.warning_journals.copy()

    if search_term:
        if search_type == "精确查询":
            display_df = display_df[
                display_df['期刊名称'].str.strip().str.lower() == search_term.strip().lower()
                ]
        else:
            display_df = display_df[
                display_df['期刊名称'].str.contains(search_term, case=False, na=False)
            ]

    # 显示结果
    if len(display_df) > 0:
        st.write(f"找到 **{len(display_df)}** 条相关记录：")
        st.dataframe(display_df, use_container_width=True)

        # 提供导出功能
        csv = display_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 导出查询结果(CSV)",
            data=csv,
            file_name=f"预警期刊查询结果_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            mime='text/csv',
        )
    else:
        st.info("未找到匹配的预警期刊记录")


def show_admin_interface():
    """科研办审核员界面"""
    tab1, tab2 = st.tabs(["🔍 备案审核", "📊 审核统计"])

    with tab1:
        show_review_interface()

    with tab2:
        show_statistics_interface()


def show_review_interface():
    """备案审核界面"""
    st.header("备案审核")

    if not st.session_state.submissions:
        st.info("暂无备案记录")
    else:
        # 审核员可以看到所有记录
        records_df = pd.DataFrame(st.session_state.submissions)

        # 添加筛选选项
        col1, col2 = st.columns(2)
        with col1:
            status_filter = st.selectbox("按状态筛选", ["全部", "待审核", "审核通过", "审核驳回"])
        with col2:
            dept_filter = st.selectbox("按科室筛选", ["全部"] + list(records_df['所属科室'].unique()))

        # 应用筛选
        filtered_df = records_df.copy()
        if status_filter != "全部":
            filtered_df = filtered_df[filtered_df['状态'] == status_filter]
        if dept_filter != "全部":
            filtered_df = filtered_df[filtered_df['所属科室'] == dept_filter]

        st.write(f"显示 **{len(filtered_df)}** 条备案记录：")

        # 逐条显示记录
        for idx, record in filtered_df.iterrows():
            show_review_record(record, idx)


def show_review_record(record, index):
    """显示单条审核记录"""
    with st.expander(f"{record['论文标题']} - {record['状态']}", expanded=True):
        col1, col2 = st.columns([2, 1])

        with col1:
            st.write(f"**备案ID**: {record['备案ID']}")
            st.write(f"**目标期刊**: {record['目标期刊']}")
            st.write(f"**第一作者**: {record['第一作者']}")
            st.write(f"**通讯作者**: {record['通讯作者']}")
            st.write(f"**所属科室**: {record['所属科室']}")
            st.write(f"**提交时间**: {record['提交时间']}")
            st.write(f"**预警状态**: {record['预警状态']}")
            # 审核员可以看到提交者信息
            if record.get('提交用户角色'):
                st.write(f"**提交者**: {record['提交用户角色']}")

            if record['预警状态'] == '历年预警期刊':
                # 显示匹配的预警期刊信息
                journal_match = st.session_state.warning_journals[
                    st.session_state.warning_journals['期刊名称'].str.lower() == record['目标期刊'].lower()
                    ]
                if not journal_match.empty:
                    st.write("**预警期刊详情**:")
                    st.dataframe(journal_match, use_container_width=True)

        with col2:
            status_color = {
                '待审核': 'orange',
                '审核通过': 'green',
                '审核驳回': 'red'
            }.get(record['状态'], 'gray')

            st.markdown(f"**当前状态**: <span style='color:{status_color}'>{record['状态']}</span>", unsafe_allow_html=True)
            st.write(f"**审核人**: {record.get('审核人', '')}")
            st.write(f"**审核时间**: {record.get('审核时间', '')}")
            st.write(f"**审核意见**: {record.get('审核意见', '')}")

            # 对于预警期刊自动驳回的记录，显示说明
            if record['状态'] == '审核驳回' and record['审核人'] == '科研办':
                st.info("🔍 此备案为系统自动驳回，因目标预警期刊为历年预警期刊，请改投其他期刊")


def show_statistics_interface():
    """统计界面"""
    st.header("审核统计")

    if not st.session_state.submissions:
        st.info("暂无备案记录")
    else:
        records_df = pd.DataFrame(st.session_state.submissions)

        # 总体统计
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_count = len(records_df)
            st.metric("总备案数", total_count)
        with col2:
            pending_count = len(records_df[records_df['状态'] == '待审核'])
            st.metric("待审核", pending_count)
        with col3:
            approved_count = len(records_df[records_df['状态'] == '审核通过'])
            st.metric("审核通过", approved_count)
        with col4:
            rejected_count = len(records_df[records_df['状态'] == '审核驳回'])
            st.metric("审核驳回", rejected_count)

        # 自动审核统计
        auto_rejected_count = len([s for s in st.session_state.submissions
                                   if s['状态'] == '审核驳回' and s['审核人'] == '科研办'])
        auto_approved_count = len([s for s in st.session_state.submissions
                                   if s['状态'] == '审核通过' and s['审核人'] == '科研办'])

        st.subheader("自动审核统计")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("自动通过", auto_approved_count)
        with col2:
            st.metric("自动驳回", auto_rejected_count)

        # 按科室统计
        st.subheader("按科室统计")
        dept_stats = records_df.groupby('所属科室')['状态'].value_counts().unstack(fill_value=0)
        st.dataframe(dept_stats, use_container_width=True)

        # 按预警状态统计
        st.subheader("按预警状态统计")
        warning_stats = records_df.groupby('预警状态')['状态'].value_counts().unstack(fill_value=0)
        st.dataframe(warning_stats, use_container_width=True)

        # 导出审核数据
        st.subheader("数据导出")
        csv = records_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 导出全部审核数据(CSV)",
            data=csv,
            file_name=f"审核数据_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            mime='text/csv',
        )


# ==================== 主程序执行 ====================
def main():
    """主程序"""
    # 初始化会话状态
    init_session_state()

    # 执行登录系统
    login_system()

    # 执行管理功能
    management_functions()

    # 执行主应用
    main_application()


if __name__ == "__main__":
    main()

    # 页脚
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "武汉亚洲心脏病医院 · 科研管理办公室 · 论文投稿备案系统 "
        "</div>",
        unsafe_allow_html=True
    )