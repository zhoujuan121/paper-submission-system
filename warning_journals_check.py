import streamlit as st
import pandas as pd
import datetime
import hashlib
import os
import json
from pathlib import Path

# 页面配置 - 必须放在最前面！（移除重复刷新逻辑，避免冲突）
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
    /* 修复休眠提示样式，增加可读性 */
    .stAlert {z-index: 9999 !important;}
    </style>
"""
st.markdown(hide_menu_style, unsafe_allow_html=True)

# 完整美化的标签页样式（调整字体大小）
tab_style_complete = """
<style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 16px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 55px;
        white-space: pre-wrap;
        background-color: #f8f9fa;
        border-radius: 8px 8px 0px 0px;
        gap: 8px;
        padding: 14px 26px;
        font-weight: bold;
        font-size: 24px !important; /* 增大标签页字体大小 */
        border: 1px solid #dee2e6;
    }

    .stTabs [aria-selected="true"] {
        background-color: #1f77b4;
        color: white;
        font-size: 24px !important; /* 增大选中标签页字体大小 */
        border: 1px solid #1f77b4;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background-color: #e9ecef;
        color: #1f77b4;
    }

    .stTabs [aria-selected="true"]:hover {
        background-color: #1f77b4;
        color: white;
    }
</style>
"""

st.markdown(tab_style_complete, unsafe_allow_html=True)

# ==================== 核心配置优化 ====================
# 数据文件路径配置（确保跨平台兼容）
DATA_FILE = Path("submissions_data.json")
# 会话超时时间（延长至2小时，单位：秒）
SESSION_TIMEOUT = 7200  # 2小时 = 7200秒
# 固定盐值（确保科研人员ID唯一且固定）
FIXED_SALT = "whayh_hospital_research_fixed_salt_2025"


# ==================== 数据持久化函数优化 ====================
def save_submissions():
    """优化：确保文件目录存在，增加写入成功验证"""
    try:
        # 确保数据文件所在目录存在
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        # 写入数据（增加错误捕获粒度）
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(st.session_state.submissions, f, ensure_ascii=False, indent=2)
        # 验证写入成功
        if DATA_FILE.exists() and os.path.getsize(DATA_FILE) > 0:
            return True
        else:
            st.error("❌ 数据保存失败：文件为空或未创建")
            return False
    except PermissionError:
        st.error("❌ 数据保存失败：无文件写入权限，请检查目录权限")
        return False
    except Exception as e:
        st.error(f"❌ 数据保存失败: {str(e)}")
        return False


def load_submissions():
    """优化：增加文件完整性校验，避免读取损坏文件"""
    try:
        if not DATA_FILE.exists():
            st.info("📁 未找到历史数据文件，将创建新文件")
            return []

        # 检查文件大小（避免空文件）
        if os.path.getsize(DATA_FILE) == 0:
            st.warning("⚠️ 数据文件为空，将重新初始化")
            return []

        # 读取并解析JSON
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # 校验数据格式（确保是列表）
        if isinstance(data, list):
            return data
        else:
            st.error("⚠️ 数据文件格式错误，将使用空数据")
            return []
    except json.JSONDecodeError:
        st.error("⚠️ 数据文件损坏，无法读取历史记录")
        # 备份损坏文件
        backup_file = DATA_FILE.with_suffix(f".bak_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}")
        DATA_FILE.rename(backup_file)
        st.info(f"损坏文件已备份为：{backup_file.name}")
        return []
    except Exception as e:
        st.error(f"❌ 加载数据失败: {str(e)}")
        return []


# ==================== 会话超时管理 ====================
def check_session_timeout():
    """检查会话是否超时，延长会话有效期"""
    current_time = datetime.datetime.now().timestamp()
    # 初始化会话时间戳
    if 'session_start_time' not in st.session_state:
        st.session_state.session_start_time = current_time
    # 检查超时（当前时间 - 会话开始时间 > 超时时间）
    if current_time - st.session_state.session_start_time > SESSION_TIMEOUT:
        # 超时处理：保存当前数据并提示
        if 'submissions' in st.session_state:
            save_submissions()  # 强制保存数据
        st.warning(f"⚠️ 会话已超时（{SESSION_TIMEOUT // 3600}小时），请刷新页面继续使用")
        # 重置会话开始时间（允许继续操作）
        st.session_state.session_start_time = current_time
    else:
        # 未超时：更新会话时间戳（刷新有效期）
        st.session_state.session_start_time = current_time


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


# ==================== 数据初始化优化 ====================
def init_session_state():
    """优化：固定身份初始化，确保科研人员ID唯一且固定（解决下次登录不显示记录问题）"""
    # 1. 会话超时检查
    check_session_timeout()

    # 2. 用户身份初始化（固定两个身份，无自定义）
    if 'user_role' not in st.session_state:
        st.session_state.user_role = "科研人员"  # 默认身份
    if 'is_authenticated' not in st.session_state:
        st.session_state.is_authenticated = False  # 默认未登录

    # 3. 固定用户名称和ID（关键修复：科研人员ID固定，确保下次登录能匹配历史记录）
    if st.session_state.user_role == "科研办审核员":
        st.session_state.current_user = "科研办管理员"
        # 固定管理员ID
        st.session_state.user_id = hashlib.md5(
            (st.session_state.current_user + FIXED_SALT).encode('utf-8')
        ).hexdigest()
    else:
        st.session_state.current_user = "科研人员"
        # 关键修复：科研人员ID固定（基于身份+固定盐值），确保每次登录ID一致
        st.session_state.user_id = hashlib.md5(
            (st.session_state.current_user + FIXED_SALT).encode('utf-8')
        ).hexdigest()

    # 4. 数据加载（优化：优先加载本地文件，确保历史记录不丢失）
    if 'submissions' not in st.session_state:
        st.session_state.submissions = load_submissions()
        # 显示加载状态
        record_count = len(st.session_state.submissions)
        if record_count == 0:
            st.info("✅ 暂无历史备案记录，可正常提交新备案")
        else:
            st.success(f"✅ 加载历史记录 {record_count} 条")

    # 5. 预警期刊初始化
    if 'warning_journals' not in st.session_state:
        init_warning_journals()
    if 'show_admin_login' not in st.session_state:
        st.session_state.show_admin_login = False
    # 6. 表单数据初始化（避免未定义报错）
    if 'paper_info' not in st.session_state:
        st.session_state.paper_info = {}
    if 'department_choice' not in st.session_state:
        st.session_state.department_choice = "心内科"
    if 'other_department_text' not in st.session_state:
        st.session_state.other_department_text = ""


# ==================== 预警期刊初始化 ====================
def init_warning_journals():
    """初始化预警期刊数据"""
    try:
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin1', 'cp1252']
        for encoding in encodings:
            try:
                df = pd.read_csv('warning_journals_20251117.csv', encoding=encoding)
                df_cleaned = clean_dataframe(df)
                if not df_cleaned.empty:
                    st.session_state.warning_journals = df_cleaned
                    return
            except (UnicodeDecodeError, LookupError):
                continue
            except Exception as e:
                continue
        st.session_state.warning_journals = create_sample_journals()
        st.warning("⚠️ 无法读取CSV文件，使用示例数据")
    except FileNotFoundError:
        st.session_state.warning_journals = create_sample_journals()
        st.info("📝 使用示例预警期刊数据，请上传CSV文件")


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
    """登录系统界面（严格权限控制）"""
    with st.sidebar:
        st.header("🔐 系统登录")

        # 显示当前身份和登录状态
        if st.session_state.is_authenticated:
            if st.session_state.user_role == "科研办审核员":
                st.success(f"✅ 当前身份：{st.session_state.current_user}（管理员）")
                # 切换至科研人员身份
                if st.button("🔁 切换至科研人员身份"):
                    st.session_state.user_role = "科研人员"
                    st.session_state.current_user = "科研人员"
                    # 重置为科研人员固定ID
                    st.session_state.user_id = hashlib.md5(
                        (st.session_state.current_user + FIXED_SALT).encode('utf-8')
                    ).hexdigest()
                    st.rerun()
            else:
                st.success(f"✅ 当前身份：{st.session_state.current_user}")
                # 切换至管理员登录
                if st.button("🔐 切换至管理员登录"):
                    st.session_state.show_admin_login = True
                    st.rerun()
        else:
            # 未登录状态：仅显示登录选项
            st.info("请选择身份登录系统")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚀 科研人员登录", use_container_width=True, type="primary"):
                    # 科研人员登录：无需密码，直接认证
                    st.session_state.user_role = "科研人员"
                    st.session_state.current_user = "科研人员"
                    st.session_state.user_id = hashlib.md5(
                        (st.session_state.current_user + FIXED_SALT).encode('utf-8')
                    ).hexdigest()
                    st.session_state.is_authenticated = True
                    st.success("✅ 科研人员登录成功！")
                    st.rerun()
            with col2:
                if st.button("🔐 管理员登录", use_container_width=True):
                    st.session_state.show_admin_login = True
                    st.rerun()

        # 管理员登录表单（仅在未登录或切换时显示）
        if st.session_state.show_admin_login:
            st.markdown("---")
            st.subheader("管理员登录验证")
            password = st.text_input(
                "请输入管理员密码",
                type="password",
                placeholder="输入管理员密码",
                key="admin_pwd"
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ 验证身份", use_container_width=True):
                    handle_admin_login(password)
            with col2:
                if st.button("❌ 取消", use_container_width=True):
                    st.session_state.show_admin_login = False
                    st.rerun()


def handle_admin_login(password):
    """处理管理员登录（严格密码验证）"""
    security_config = get_security_config()
    correct_password = security_config['admin_password']
    if password == correct_password:
        st.session_state.user_role = "科研办审核员"
        st.session_state.current_user = "科研办管理员"
        st.session_state.user_id = hashlib.md5(
            (st.session_state.current_user + FIXED_SALT).encode('utf-8')
        ).hexdigest()
        st.session_state.is_authenticated = True
        st.session_state.show_admin_login = False
        st.success("✅ 管理员身份验证成功！")
        st.rerun()
    else:
        st.error("❌ 密码错误，请重新输入")


# ==================== 管理功能 ====================
def management_functions():
    """管理功能界面（严格权限控制：仅管理员可见完整功能）"""
    with st.sidebar:
        st.markdown("---")
        st.header("🔧 系统功能")

        # 预警期刊库更新（仅管理员可操作）
        st.subheader("预警期刊管理")
        if st.session_state.user_role == "科研办审核员":
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
            st.info("🔒 期刊库更新功能仅限管理员使用")

        # 系统统计（权限区分：管理员看全部，科研人员看自己的）
        st.markdown("---")
        st.subheader("📊 数据统计")
        st.write(f"预警期刊数量: **{len(st.session_state.warning_journals)}** 种")

        if st.session_state.user_role == "科研办审核员":
            # 管理员：显示全量统计
            total_count = len(st.session_state.submissions)
            st.write(f"总备案数量: **{total_count}** 条")
            if st.session_state.submissions:
                records_df = pd.DataFrame(st.session_state.submissions)
                pending_count = len(records_df[records_df['状态'] == '待审核'])
                approved_count = len(records_df[records_df['状态'] == '审核通过'])
                rejected_count = len(records_df[records_df['状态'] == '审核驳回'])
                st.write(f"待审核: **{pending_count}** 条")
                st.write(f"已通过: **{approved_count}** 条")
                st.write(f"已驳回: **{rejected_count}** 条")
        else:
            # 科研人员：仅显示自己的统计
            my_count = len([s for s in st.session_state.submissions if s.get('提交用户ID') == st.session_state.user_id])
            st.write(f"我的备案数量: **{my_count}** 条")
            if my_count > 0:
                my_submissions = [s for s in st.session_state.submissions if
                                  s.get('提交用户ID') == st.session_state.user_id]
                approved_count = len([s for s in my_submissions if s.get('状态') == '审核通过'])
                rejected_count = len([s for s in my_submissions if s.get('状态') == '审核驳回'])
                st.write(f"已通过: **{approved_count}** 条")
                st.write(f"已驳回: **{rejected_count}** 条")


# ==================== 主应用功能 ====================
def main_application():
    """主应用界面（严格权限区分）"""
    st.title("📚 论文投稿备案与期刊预警系统")

    # 未登录提示
    if not st.session_state.is_authenticated:
        st.warning("🔐 请先通过左侧菜单登录系统，再使用相关功能")
        return

    # 已登录：根据身份显示不同界面
    if st.session_state.user_role == "科研人员":
        show_researcher_interface()
    else:
        show_admin_interface()


def show_researcher_interface():
    """科研人员界面（仅显示个人相关功能）"""
    tab1, tab2, tab3 = st.tabs(["🔍 预警期刊查询", "📝 投稿备案", "📋 我的备案记录"])
    with tab1:
        show_journal_search_interface()
    with tab2:
        show_submission_interface()
    with tab3:
        show_my_submissions()


def show_journal_search_interface():
    """期刊查询界面（科研人员和管理员共用，无权限限制）"""
    st.header("预警期刊查询")

    # 搜索功能
    col1, col2 = st.columns([2, 1])
    with col1:
        search_term = st.text_input("🔍 搜索期刊名称", placeholder="输入期刊名称关键词")
    with col2:
        search_type = st.selectbox("查询方式", ["模糊查询", "精确查询"])

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
        # 导出功能
        csv = display_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 导出查询结果(CSV)",
            data=csv,
            file_name=f"预警期刊查询结果_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            mime='text/csv',
        )
    else:
        st.info("未找到匹配的预警期刊记录")


def show_submission_interface():
    """投稿备案界面（仅科研人员可使用）"""
    st.header("论文投稿备案")

    # 论文基本信息
    st.subheader("📄 论文基本信息")
    col1, col2 = st.columns(2)
    with col1:
        paper_title = st.text_input("论文标题*", placeholder="请输入完整的论文标题",
                                    value=st.session_state.paper_info.get('paper_title', ''))
        authors = st.text_input("第一作者*", placeholder="第一作者姓名",
                                value=st.session_state.paper_info.get('authors', ''))
        corresponding_author = st.text_input("通讯作者*", placeholder="通讯作者姓名",
                                             value=st.session_state.paper_info.get('corresponding_author', ''))
    with col2:
        target_journal = st.text_input("目标期刊名称*", placeholder="请输入完整的期刊名称",
                                       value=st.session_state.paper_info.get('target_journal', ''))
        planned_submission_date = st.date_input("拟投稿日期",
                                                value=st.session_state.paper_info.get('planned_submission_date',
                                                                                      datetime.date.today()))

    # 实时保存论文信息
    if all([paper_title, authors, corresponding_author, target_journal]):
        st.session_state.paper_info = {
            'paper_title': paper_title,
            'authors': authors,
            'corresponding_author': corresponding_author,
            'target_journal': target_journal,
            'planned_submission_date': planned_submission_date
        }

    # 科室信息
    st.markdown("---")
    st.subheader("🏥 科室信息")
    col_dept1, col_dept2 = st.columns([1, 1])
    with col_dept1:
        department_options = [
            "心内科", "心外科", "超声科", "放射科", "体外循环科",
            "麻醉科", "检验科", "输血科", "心功能科", '护理部', '药学部', '其他'
        ]
        department = st.selectbox(
            "选择所属科室*",
            department_options,
            key="department_select",
            index=department_options.index(st.session_state.department_choice)
        )
        st.session_state.department_choice = department

    with col_dept2:
        if st.session_state.department_choice == '其他':
            other_department = st.text_input(
                "请填写具体科室名称*",
                placeholder="请输入您的具体科室名称",
                value=st.session_state.other_department_text,
                key="other_department_input"
            )
            st.session_state.other_department_text = other_department
            if not other_department:
                st.warning("⚠️ 请填写具体科室名称")
            else:
                st.success(f"✅ 已填写: **{other_department}**")
        else:
            st.session_state.other_department_text = ""
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            st.success(f"✅ 已选择: **{st.session_state.department_choice}**")

    # 显示当前科室
    final_department = (
        st.session_state.other_department_text
        if st.session_state.department_choice == '其他' else st.session_state.department_choice
    )
    st.info(f"**当前选择科室**: {final_department}")

    # 确认提交（所有必填项完成后显示）
    if (st.session_state.paper_info and
            st.session_state.department_choice and
            not (st.session_state.department_choice == '其他' and not st.session_state.other_department_text)):
        st.markdown("---")
        st.subheader("✅ 确认提交")
        with st.form("confirmation_form"):
            st.markdown("### 备案信息汇总")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**论文标题**: {st.session_state.paper_info['paper_title']}")
                st.write(f"**第一作者**: {st.session_state.paper_info['authors']}")
                st.write(f"**通讯作者**: {st.session_state.paper_info['corresponding_author']}")
            with col2:
                st.write(f"**目标期刊**: {st.session_state.paper_info['target_journal']}")
                st.write(f"**拟投稿日期**: {st.session_state.paper_info['planned_submission_date']}")
                st.write(f"**所属科室**: {final_department}")

            st.markdown("**注意**: 提交后无法修改，请确认信息无误！")
            submitted = st.form_submit_button("🚀 提交备案申请", type="primary")

            if submitted:
                handle_submission(
                    paper_title, authors, corresponding_author,
                    st.session_state.department_choice, st.session_state.other_department_text,
                    target_journal, planned_submission_date
                )
                # 清理表单
                st.session_state.paper_info = {}
                st.session_state.department_choice = "心内科"
                st.session_state.other_department_text = ""
                st.success("✅ 备案申请已提交！")
    else:
        # 提示未完成的必填项
        missing_fields = []
        if not st.session_state.paper_info:
            missing_fields.append("论文基本信息")
        if st.session_state.department_choice == '其他' and not st.session_state.other_department_text:
            missing_fields.append("具体科室名称")
        if missing_fields:
            st.info(f"📝 请先完善以下必填信息：{', '.join(missing_fields)}")


def handle_submission(paper_title, authors, corresponding_author, department, other_department, target_journal,
                      planned_submission_date):
    """处理投稿备案（关联当前用户ID，确保仅本人可见）"""
    # 确定最终科室
    final_department = other_department if department == '其他' else department

    # 检查期刊是否在预警列表
    journal_match = st.session_state.warning_journals[
        st.session_state.warning_journals['期刊名称'].str.lower() == target_journal.lower()
        ]

    # 生成备案信息（关键：关联当前用户ID）
    record_id = f"BA{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    beijing_time = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    submission_data = {
        '备案ID': record_id,
        '论文标题': paper_title,
        '第一作者': authors,
        '通讯作者': corresponding_author,
        '目标期刊': target_journal,
        '所属科室': final_department,
        '拟投稿日期': planned_submission_date.strftime("%Y-%m-%d"),
        '提交时间': beijing_time.strftime("%Y-%m-%d %H:%M:%S"),
        '预警状态': '历年预警期刊' if not journal_match.empty else '安全',
        '提交用户ID': st.session_state.user_id,  # 关联当前用户ID
        '提交用户角色': st.session_state.user_role,
        '审核人': '科研办',
        '审核时间': beijing_time.strftime("%Y-%m-%d %H:%M:%S")
    }

    # 自动审核逻辑
    if not journal_match.empty:
        st.error("⚠️ **预警提醒**")
        st.write(f"您选择的期刊 **'{target_journal}'** 属于预警期刊！")
        st.dataframe(journal_match, use_container_width=True)
        st.error("❌ 备案申请已自动驳回")
        # 显示重要提示
        st.markdown(
            """
            <div style='color: #d32f2f; font-size: 18px; font-weight: bold; padding: 15px; border: 2px solid #d32f2f; border-radius: 8px; background-color: #ffebee; margin: 10px 0; text-align: center;'>
            ⭐⭐⭐ 重要提示 ⭐⭐⭐<br>
            在此期刊上发表论文将无法报销并奖励，请改投其他期刊
            </div>
            """,
            unsafe_allow_html=True
        )
        submission_data['状态'] = '审核驳回'
        submission_data['审核意见'] = '历年预警期刊，不予报销奖励，请改投其他期刊'
    else:
        st.success("✅ **期刊校验通过，备案已自动完成！**")
        submission_data['状态'] = '审核通过'
        submission_data['审核意见'] = '无预警，自动通过，可投稿'

    # 保存记录（关联用户ID）
    st.session_state.submissions.append(submission_data)
    save_submissions()

    # 显示提交摘要
    st.markdown("---")
    st.subheader("备案信息摘要")
    summary_data = {k: v for k, v in submission_data.items() if k not in ['提交用户ID', '提交用户角色']}
    st.dataframe(pd.DataFrame([summary_data]), use_container_width=True)


def show_my_submissions():
    """显示当前科研人员的备案记录（仅筛选自己的记录）"""
    st.header("我的备案记录")

    # 关键筛选：仅保留当前用户ID匹配的记录
    user_submissions = [s for s in st.session_state.submissions if s.get('提交用户ID') == st.session_state.user_id]

    if not user_submissions:
        st.info("ℹ️ 您还没有提交过备案记录，可通过「投稿备案」功能提交")
        return

    st.write(f"您共有 **{len(user_submissions)}** 条备案记录：")

    # 转换为DataFrame显示
    display_data = []
    for s in user_submissions:
        display_item = {
            '备案ID': s['备案ID'],
            '论文标题': s['论文标题'],
            '目标期刊': s['目标期刊'],
            '第一作者': s['第一作者'],
            '所属科室': s['所属科室'],
            '提交时间': s['提交时间'],
            '预警状态': s['预警状态'],
            '审核状态': s['状态'],
            '审核意见': s['审核意见']
        }
        display_data.append(display_item)
    df = pd.DataFrame(display_data)

    # 筛选功能
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox("按审核状态筛选", ["全部", "审核通过", "审核驳回"])
    with col2:
        warning_filter = st.selectbox("按预警状态筛选", ["全部", "安全", "历年预警期刊"])

    # 应用筛选
    filtered_df = df.copy()
    if status_filter != "全部":
        filtered_df = filtered_df[filtered_df['审核状态'] == status_filter]
    if warning_filter != "全部":
        filtered_df = filtered_df[filtered_df['预警状态'] == warning_filter]

    st.write(f"显示 **{len(filtered_df)}** 条记录：")
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

    # 导出个人记录功能
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 导出我的备案记录",
        data=csv,
        file_name=f"我的备案记录_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
        mime='text/csv'
    )


def show_admin_interface():
    """管理员界面（仅显示全量审核和统计功能）"""
    tab1, tab2 = st.tabs(["🔍 全量备案审核", "📊 系统审核统计"])
    with tab1:
        show_admin_review_interface()
    with tab2:
        show_admin_statistics_interface()


def show_admin_review_interface():
    """管理员备案审核（可查看所有用户的备案记录）"""
    st.header("全量备案审核")

    if not st.session_state.submissions:
        st.info("暂无备案记录")
        return

    # 全量记录显示
    records_df = pd.DataFrame(st.session_state.submissions)
    st.write(f"系统共有 **{len(records_df)}** 条备案记录：")

    # 高级筛选
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox("按审核状态筛选", ["全部", "审核通过", "审核驳回"])
    with col2:
        dept_filter = st.selectbox("按科室筛选", ["全部"] + list(records_df['所属科室'].unique()))
    with col3:
        warning_filter = st.selectbox("按预警状态筛选", ["全部", "安全", "历年预警期刊"])

    # 应用筛选
    filtered_df = records_df.copy()
    if status_filter != "全部":
        filtered_df = filtered_df[filtered_df['状态'] == status_filter]
    if dept_filter != "全部":
        filtered_df = filtered_df[filtered_df['所属科室'] == dept_filter]
    if warning_filter != "全部":
        filtered_df = filtered_df[filtered_df['预警状态'] == warning_filter]

    st.write(f"当前显示 **{len(filtered_df)}** 条记录：")

    # 逐条展开显示详情
    for idx, record in filtered_df.iterrows():
        with st.expander(f"备案ID: {record['备案ID']} | {record['论文标题']} | 状态: {record['状态']}", expanded=False):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write(f"**论文标题**: {record['论文标题']}")
                st.write(f"**第一作者**: {record['第一作者']}")
                st.write(f"**通讯作者**: {record['通讯作者']}")
                st.write(f"**目标期刊**: {record['目标期刊']}")
                st.write(f"**所属科室**: {record['所属科室']}")
                st.write(f"**拟投稿日期**: {record['拟投稿日期']}")
                st.write(f"**提交时间**: {record['提交时间']}")
                st.write(f"**提交用户**: {record['提交用户角色']}")
                # 预警期刊详情
                if record['预警状态'] == '历年预警期刊':
                    journal_match = st.session_state.warning_journals[
                        st.session_state.warning_journals['期刊名称'].str.lower() == record['目标期刊'].lower()
                        ]
                    st.write("**预警期刊详情**:")
                    st.dataframe(journal_match[['期刊名称', '预警年份', '预警来源']], use_container_width=True)
            with col2:
                st.markdown(
                    f"**审核状态**: <span style='color: {'green' if record['状态'] == '审核通过' else 'red'}'>{record['状态']}</span>",
                    unsafe_allow_html=True)
                st.write(f"**预警状态**: {record['预警状态']}")
                st.write(f"**审核人**: {record['审核人']}")
                st.write(f"**审核时间**: {record['审核时间']}")
                st.write(f"**审核意见**: {record['审核意见']}")


def show_admin_statistics_interface():
    """管理员统计界面（全量数据统计）"""
    st.header("系统审核统计分析")

    if not st.session_state.submissions:
        st.info("暂无备案记录，无法生成统计数据")
        return

    records_df = pd.DataFrame(st.session_state.submissions)

    # 1. 总体统计
    st.subheader("1. 总体数据统计")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总备案数", len(records_df))
    with col2:
        st.metric("审核通过数", len(records_df[records_df['状态'] == '审核通过']))
    with col3:
        st.metric("审核驳回数", len(records_df[records_df['状态'] == '审核驳回']))
    with col4:
        st.metric("预警期刊占比", f"{len(records_df[records_df['预警状态'] == '历年预警期刊']) / len(records_df) * 100:.1f}%")

    # 2. 按科室统计
    st.subheader("2. 按科室统计")
    dept_stats = records_df.groupby('所属科室')['状态'].value_counts().unstack(fill_value=0)
    st.dataframe(dept_stats, use_container_width=True)

    # 3. 按预警状态统计
    st.subheader("3. 按预警状态统计")
    warning_stats = records_df.groupby('预警状态')['状态'].value_counts().unstack(fill_value=0)
    st.dataframe(warning_stats, use_container_width=True)

    # 4. 时间趋势统计（按提交日期分组）
    st.subheader("4. 提交时间趋势")
    records_df['提交日期'] = pd.to_datetime(records_df['提交时间']).dt.date
    time_trend = records_df.groupby('提交日期').size().reset_index(name='备案数量')
    st.line_chart(time_trend, x='提交日期', y='备案数量', use_container_width=True)

    # 5. 全量数据导出
    st.subheader("5. 数据导出")
    csv = records_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 导出全量备案数据(CSV)",
        data=csv,
        file_name=f"全量备案数据_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
        mime='text/csv',
        type="primary"
    )


# ==================== 主程序执行 ====================
def main():
    """主程序（初始化+权限控制）"""
    # 初始化会话状态
    init_session_state()

    # 登录系统（权限控制入口）
    login_system()

    # 显示管理功能（侧边栏）
    management_functions()

    # 显示主应用界面（根据身份区分）
    main_application()

    # 页脚
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray; font-size: 14px;'>"
        "武汉亚洲心脏病医院 · 科研管理办公室 · 论文投稿备案系统 | 系统版本：V1.0"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()