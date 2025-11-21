import streamlit as st
import pandas as pd
import datetime
import hashlib
import os
import json
import atexit
import sqlite3
import base64

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


# ==================== 增强的数据持久化方案 ====================

class DatabaseManager:
    """数据库管理器 - 提供持久化数据存储"""

    def __init__(self, db_path='submissions.db'):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建投稿备案表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT UNIQUE,
                paper_title TEXT NOT NULL,
                authors TEXT NOT NULL,
                corresponding_author TEXT NOT NULL,
                department TEXT NOT NULL,
                target_journal TEXT NOT NULL,
                planned_submission_date TEXT,
                submission_time TEXT NOT NULL,
                warning_status TEXT NOT NULL,
                status TEXT NOT NULL,
                review_comment TEXT,
                reviewer TEXT,
                review_time TEXT,
                user_id TEXT NOT NULL,
                user_role TEXT NOT NULL
            )
        ''')

        # 创建预警期刊表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warning_journals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                journal_name TEXT UNIQUE NOT NULL,
                warning_year INTEGER,
                warning_source TEXT
            )
        ''')

        conn.commit()
        conn.close()

    def save_submission(self, submission_data):
        """保存投稿备案记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO submissions 
                (record_id, paper_title, authors, corresponding_author, department, 
                 target_journal, planned_submission_date, submission_time, warning_status,
                 status, review_comment, reviewer, review_time, user_id, user_role)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                submission_data['备案ID'],
                submission_data['论文标题'],
                submission_data['第一作者'],
                submission_data['通讯作者'],
                submission_data['所属科室'],
                submission_data['目标期刊'],
                submission_data.get('拟投稿日期', ''),
                submission_data['提交时间'],
                submission_data['预警状态'],
                submission_data['状态'],
                submission_data.get('审核意见', ''),
                submission_data.get('审核人', ''),
                submission_data.get('审核时间', ''),
                submission_data['提交用户ID'],
                submission_data['提交用户角色']
            ))

            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # 记录已存在，更新记录
            cursor.execute('''
                UPDATE submissions SET
                paper_title=?, authors=?, corresponding_author=?, department=?,
                target_journal=?, planned_submission_date=?, submission_time=?,
                warning_status=?, status=?, review_comment=?, reviewer=?, review_time=?,
                user_id=?, user_role=?
                WHERE record_id=?
            ''', (
                submission_data['论文标题'],
                submission_data['第一作者'],
                submission_data['通讯作者'],
                submission_data['所属科室'],
                submission_data['目标期刊'],
                submission_data.get('拟投稿日期', ''),
                submission_data['提交时间'],
                submission_data['预警状态'],
                submission_data['状态'],
                submission_data.get('审核意见', ''),
                submission_data.get('审核人', ''),
                submission_data.get('审核时间', ''),
                submission_data['提交用户ID'],
                submission_data['提交用户角色'],
                submission_data['备案ID']
            ))

            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            st.error(f"保存数据失败: {e}")
            return False
        finally:
            conn.close()

    def load_submissions(self, user_id=None, user_role=None):
        """加载投稿备案记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            if user_role == "科研办审核员":
                # 审核员可以看到所有记录
                cursor.execute('SELECT * FROM submissions ORDER BY submission_time DESC')
            else:
                # 科研人员只能看到自己的记录
                cursor.execute('''
                    SELECT * FROM submissions 
                    WHERE user_id = ? 
                    ORDER BY submission_time DESC
                ''', (user_id,))

            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

            submissions = []
            for row in rows:
                submission = dict(zip(columns, row))
                # 转换为前端需要的格式
                submissions.append({
                    '备案ID': submission['record_id'],
                    '论文标题': submission['paper_title'],
                    '第一作者': submission['authors'],
                    '通讯作者': submission['corresponding_author'],
                    '所属科室': submission['department'],
                    '目标期刊': submission['target_journal'],
                    '拟投稿日期': submission['planned_submission_date'],
                    '提交时间': submission['submission_time'],
                    '预警状态': submission['warning_status'],
                    '状态': submission['status'],
                    '审核意见': submission['review_comment'],
                    '审核人': submission['reviewer'],
                    '审核时间': submission['review_time'],
                    '提交用户ID': submission['user_id'],
                    '提交用户角色': submission['user_role']
                })

            return submissions
        except Exception as e:
            st.error(f"加载数据失败: {e}")
            return []
        finally:
            conn.close()

    def save_warning_journals(self, journals_df):
        """保存预警期刊数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 清空现有数据
            cursor.execute('DELETE FROM warning_journals')

            # 插入新数据
            for _, row in journals_df.iterrows():
                cursor.execute('''
                    INSERT INTO warning_journals (journal_name, warning_year, warning_source)
                    VALUES (?, ?, ?)
                ''', (
                    row['期刊名称'],
                    row.get('预警年份', 2023),
                    row.get('预警来源', '中科院预警')
                ))

            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            st.error(f"保存预警期刊失败: {e}")
            return False
        finally:
            conn.close()

    def load_warning_journals(self):
        """加载预警期刊数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT journal_name, warning_year, warning_source FROM warning_journals')
            rows = cursor.fetchall()

            if rows:
                journals_df = pd.DataFrame(rows, columns=['期刊名称', '预警年份', '预警来源'])
                return journals_df
            else:
                return create_sample_journals()
        except Exception as e:
            st.error(f"加载预警期刊失败: {e}")
            return create_sample_journals()
        finally:
            conn.close()

    def get_statistics(self):
        """获取统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 总备案数
            cursor.execute('SELECT COUNT(*) FROM submissions')
            total_count = cursor.fetchone()[0]

            # 各状态数量
            cursor.execute('SELECT status, COUNT(*) FROM submissions GROUP BY status')
            status_counts = dict(cursor.fetchall())

            # 各科室数量
            cursor.execute('SELECT department, COUNT(*) FROM submissions GROUP BY department')
            dept_counts = dict(cursor.fetchall())

            # 预警期刊数量
            cursor.execute('SELECT COUNT(*) FROM warning_journals')
            warning_count = cursor.fetchone()[0]

            return {
                'total_count': total_count,
                'status_counts': status_counts,
                'dept_counts': dept_counts,
                'warning_count': warning_count
            }
        except Exception as e:
            st.error(f"获取统计信息失败: {e}")
            return {}
        finally:
            conn.close()


# 全局数据库管理器实例
db_manager = DatabaseManager()


# 增强保存函数 - 现在使用数据库
def save_submissions():
    """保存备案数据到数据库"""
    try:
        # 数据现在实时保存到数据库，这里主要更新session state
        if 'submissions' in st.session_state:
            # 确保session state与数据库同步
            st.session_state.submissions = db_manager.load_submissions(
                st.session_state.user_id,
                st.session_state.user_role
            )
        st.session_state.last_save_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        st.error(f"保存数据失败: {e}")


# 注册退出时的自动保存 - 移到函数定义之后
atexit.register(save_submissions)


def load_submissions():
    """从数据库加载备案数据"""
    return db_manager.load_submissions(st.session_state.user_id, st.session_state.user_role)


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
        st.session_state.is_authenticated = True
    if 'submissions' not in st.session_state:
        st.session_state.submissions = load_submissions()
    if 'warning_journals' not in st.session_state:
        st.session_state.warning_journals = db_manager.load_warning_journals()
    if 'show_admin_login' not in st.session_state:
        st.session_state.show_admin_login = False
    if 'current_user' not in st.session_state:
        st.session_state.current_user = "科研人员"
    if 'user_id' not in st.session_state:
        # 生成更稳定的用户ID（基于时间戳和随机数）
        st.session_state.user_id = f"user_{int(datetime.datetime.now().timestamp())}_{hashlib.md5(str(os.urandom(8)).encode()).hexdigest()[:8]}"
    if 'last_save_time' not in st.session_state:
        st.session_state.last_save_time = "尚未保存"
    if 'db_initialized' not in st.session_state:
        st.session_state.db_initialized = True


def init_warning_journals():
    """初始化预警期刊数据 - 现在从数据库加载"""
    st.session_state.warning_journals = db_manager.load_warning_journals()


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


def show_data_status():
    """显示数据状态"""
    with st.sidebar:
        st.markdown("---")
        st.subheader("📊 数据状态")

        stats = db_manager.get_statistics()
        total_count = stats.get('total_count', 0)
        warning_count = stats.get('warning_count', 0)

        st.write(f"备案记录: **{total_count}** 条")
        st.write(f"预警期刊: **{warning_count}** 种")

        if 'last_save_time' in st.session_state:
            st.write(f"最后同步: {st.session_state.last_save_time}")

        # 数据备份功能
        if total_count > 0:
            st.download_button(
                label="💾 备份数据",
                data=json.dumps(st.session_state.submissions, ensure_ascii=False, indent=2),
                file_name=f"备案数据备份_{datetime.datetime.now().strftime('%Y%m%d')}.json",
                mime='application/json',
            )


# ==================== 登录系统 ====================
def login_system():
    """登录系统界面"""
    try:
        with st.sidebar:
            st.header("🔐 系统登录")

            # 显示当前身份
            if st.session_state.user_role == "科研办审核员":
                st.success("✅ 当前身份：科研办审核员")
                if st.button("🔁 切换至科研人员身份"):
                    st.session_state.user_role = "科研人员"
                    st.session_state.is_authenticated = True
                    st.session_state.current_user = "科研人员"
                    st.session_state.user_id = f"user_{int(datetime.datetime.now().timestamp())}_{hashlib.md5(str(os.urandom(8)).encode()).hexdigest()[:8]}"
                    st.session_state.submissions = load_submissions()  # 重新加载数据
                    st.rerun()
            else:
                st.success("👤 当前身份：科研人员")
                if st.button("🔐 管理员登录"):
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
                        st.rerun()
    except Exception as e:
        st.sidebar.error(f"侧边栏错误: {e}")


def handle_admin_login(password):
    """处理管理员登录"""
    security_config = get_security_config()
    correct_password = security_config['admin_password']

    if password == correct_password:
        st.session_state.user_role = "科研办审核员"
        st.session_state.is_authenticated = True
        st.session_state.current_user = "科研办管理员"
        st.session_state.show_admin_login = False
        st.session_state.submissions = load_submissions()  # 重新加载所有数据
        st.success("✅ 管理员身份验证成功！")
        st.rerun()
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
                    if db_manager.save_warning_journals(df_cleaned):
                        st.session_state.warning_journals = db_manager.load_warning_journals()
                        st.success(f"✅ 成功更新预警期刊库！共 {len(df_cleaned)} 条记录。")
                except Exception as e:
                    st.error(f"❌ 文件读取错误: {e}")
        else:
            st.subheader("更新预警期刊库")
            st.info("🔒 此功能仅限科研办审核员使用")

        # 显示统计信息
        st.markdown("---")
        st.subheader("📊 系统统计")
        stats = db_manager.get_statistics()

        st.write(f"预警期刊数量: **{stats.get('warning_count', 0)}** 种")
        st.write(f"总备案数量: **{stats.get('total_count', 0)}** 条")

        # 审核统计（仅科研办可见）
        if st.session_state.user_role == "科研办审核员":
            status_counts = stats.get('status_counts', {})
            st.write(f"待审核: **{status_counts.get('待审核', 0)}** 条")
            st.write(f"已通过: **{status_counts.get('审核通过', 0)}** 条")
            st.write(f"已驳回: **{status_counts.get('审核驳回', 0)}** 条")


# ==================== 主应用功能 ====================
def main_application():
    """主应用界面"""
    # 应用标题和描述
    st.title("📚 论文投稿备案与期刊预警系统")

    # 显示数据持久化状态
    st.sidebar.success("💾 数据已持久化保存")

    # 直接显示科研人员界面，跳过欢迎页面
    if st.session_state.user_role == "科研人员":
        show_researcher_interface()
    else:
        show_admin_interface()


def show_researcher_interface():
    """科研人员界面"""
    tab1, tab2, tab3 = st.tabs(["🔍 预警期刊查询", "📝 投稿备案", "📋 我的备案记录"])

    with tab1:
        show_journal_search_interface()

    with tab2:
        show_submission_interface()

    with tab3:
        show_my_submissions()


def show_journal_search_interface():
    """期刊查询界面"""
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
            # 精确匹配期刊名称
            display_df = display_df[
                display_df['期刊名称'].str.strip().str.lower() == search_term.strip().lower()
                ]
        else:
            # 模糊查询（包含关系）
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


def show_submission_interface():
    """投稿备案界面"""
    st.header("论文投稿备案")

    # 使用 session state 来跟踪所有数据
    if 'paper_info' not in st.session_state:
        st.session_state.paper_info = {}
    if 'department_choice' not in st.session_state:
        st.session_state.department_choice = "心内科"
    if 'other_department_text' not in st.session_state:
        st.session_state.other_department_text = ""

    # 第一个表单：论文基本信息（无保存按钮，直接填写）
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

    # 实时保存论文信息到session state
    if all([paper_title, authors, corresponding_author, target_journal]):
        st.session_state.paper_info = {
            'paper_title': paper_title,
            'authors': authors,
            'corresponding_author': corresponding_author,
            'target_journal': target_journal,
            'planned_submission_date': planned_submission_date
        }

    # 第二个部分：科室选择（独立部分，无需表单，即时响应）
    st.markdown("---")
    st.subheader("🏥 科室信息")

    col_dept1, col_dept2 = st.columns([1, 1])

    with col_dept1:
        # 科室选择
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

        # 实时更新session state
        st.session_state.department_choice = department

    with col_dept2:
        # 动态显示其他科室输入框或状态提示
        if st.session_state.department_choice == '其他':
            other_department = st.text_input(
                "请填写具体科室名称*",
                placeholder="请输入您的具体科室名称",
                value=st.session_state.other_department_text,
                key="other_department_input",
                help="如果您选择的科室不在列表中，请在此填写具体科室名称"
            )
            # 实时更新session state
            st.session_state.other_department_text = other_department

            # 显示填写状态
            if not other_department:
                st.warning("⚠️ 请填写具体科室名称")
            else:
                st.success(f"✅ 已填写: **{other_department}**")
        else:
            other_department = ""
            st.session_state.other_department_text = ""
            # 添加一些垂直空间来与选择框对齐
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            st.success(f"✅ 已选择: **{st.session_state.department_choice}**")

    # 显示当前选择的科室信息
    if st.session_state.department_choice == '其他' and st.session_state.other_department_text:
        st.info(f"**当前选择科室**: {st.session_state.other_department_text}")
    else:
        st.info(f"**当前选择科室**: {st.session_state.department_choice}")

    # 第三个表单：确认提交（只有在所有信息都填写完整后才显示）
    if (st.session_state.paper_info and
            st.session_state.department_choice and
            not (st.session_state.department_choice == '其他' and not st.session_state.other_department_text)):

        st.markdown("---")
        st.subheader("✅ 确认提交")

        with st.form("confirmation_form"):
            # 显示汇总信息
            st.markdown("### 备案信息汇总")

            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**论文标题**: {st.session_state.paper_info['paper_title']}")
                st.write(f"**第一作者**: {st.session_state.paper_info['authors']}")
                st.write(f"**通讯作者**: {st.session_state.paper_info['corresponding_author']}")

            with col2:
                st.write(f"**目标期刊**: {st.session_state.paper_info['target_journal']}")
                st.write(f"**拟投稿日期**: {st.session_state.paper_info['planned_submission_date']}")

                # 确定最终科室名称
                final_department = (
                    st.session_state.other_department_text
                    if st.session_state.department_choice == '其他'
                    else st.session_state.department_choice
                )
                st.write(f"**所属科室**: {final_department}")

            st.markdown("**注意**: 带 * 的字段为必填项，请确认以上信息无误")

            submitted = st.form_submit_button("🚀 提交备案申请")

            if submitted:
                # 调用处理函数
                handle_submission(
                    st.session_state.paper_info['paper_title'],
                    st.session_state.paper_info['authors'],
                    st.session_state.paper_info['corresponding_author'],
                    st.session_state.department_choice,
                    st.session_state.other_department_text,
                    st.session_state.paper_info['target_journal'],
                    st.session_state.paper_info['planned_submission_date']
                )

                # 清理session state
                st.session_state.paper_info = {}
                st.session_state.department_choice = "心内科"
                st.session_state.other_department_text = ""

                st.success("✅ 备案申请已提交！")
    else:
        # 显示缺少的信息提示
        missing_fields = []
        if not st.session_state.paper_info:
            missing_fields.append("论文基本信息")
        if not st.session_state.department_choice:
            missing_fields.append("科室信息")
        if st.session_state.department_choice == '其他' and not st.session_state.other_department_text:
            missing_fields.append("具体科室名称")

        if missing_fields:
            st.info(f"📝 请先完善以下信息：{', '.join(missing_fields)}")


def handle_submission(paper_title, authors, corresponding_author, department, other_department, target_journal,
                      planned_submission_date):
    """处理投稿备案"""
    # 基本验证
    if not all([paper_title, authors, corresponding_author, target_journal]):
        st.error("❌ 请填写所有必填字段！")
        return

    # 从session state获取最新的科室信息
    current_department = st.session_state.department_choice
    current_other_department = st.session_state.other_department_text

    # 如果选择了"其他"，必须填写具体科室
    if current_department == '其他' and not current_other_department:
        st.error("❌ 请填写具体科室名称！")
        return

    # 确定最终科室名称
    final_department = current_other_department if current_department == '其他' else current_department

    # 检查期刊是否在预警列表中
    journal_match = st.session_state.warning_journals[
        st.session_state.warning_journals['期刊名称'].str.lower() == target_journal.lower()
        ]

    # 生成备案ID
    record_id = f"BA{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

    utc_time = datetime.datetime.utcnow()
    beijing_time = utc_time + datetime.timedelta(hours=8)

    submission_data = {
        '备案ID': record_id,
        '论文标题': paper_title,
        '第一作者': authors,
        '目标期刊': target_journal,
        '通讯作者': corresponding_author,
        '所属科室': final_department,
        '拟投稿日期': str(planned_submission_date),
        '提交时间': beijing_time.strftime("%Y-%m-%d %H:%M:%S"),
        '预警状态': '历年预警期刊' if not journal_match.empty else '安全',
        '提交用户ID': st.session_state.user_id,
        '提交用户角色': st.session_state.user_role
    }

    if not journal_match.empty:
        st.error("⚠️ **预警提醒**")
        st.write(f"您选择的期刊 **'{target_journal}'** 在以下预警列表中：")
        st.dataframe(journal_match, use_container_width=True)
        st.error("❌ **您的备案申请已被驳回**")

        # 重要提示样式
        st.markdown(
            """
            <div style='
                color: #d32f2f; 
                font-size: 22px; 
                font-weight: bold; 
                padding: 20px; 
                border: 3px solid #d32f2f; 
                border-radius: 8px; 
                background-color: #ffebee;
                margin: 15px 0;
                text-align: center;
            '>
            ⭐⭐⭐ <strong>重要提示</strong> ⭐⭐⭐<br>
            在此期刊上发表论文将无法报销并奖励，请改投其他期刊
            </div>
            """,
            unsafe_allow_html=True
        )

        submission_data['状态'] = '审核驳回'
        submission_data['审核意见'] = '历年预警期刊，不予报销奖励，请改投其他期刊'
        submission_data['审核人'] = '科研办'
        submission_data['审核时间'] = beijing_time.strftime("%Y-%m-%d %H:%M:%S")

    else:
        st.success("✅ **期刊校验通过，备案已自动完成！**")
        submission_data['状态'] = '审核通过'
        submission_data['审核意见'] = '无预警，自动通过，可投稿'
        submission_data['审核人'] = '科研办'
        submission_data['审核时间'] = beijing_time.strftime("%Y-%m-%d %H:%M:%S")

    # 保存提交记录到数据库
    if db_manager.save_submission(submission_data):
        # 更新session state
        st.session_state.submissions = load_submissions()
        save_submissions()  # 更新保存时间

        # 显示提交摘要
        st.markdown("---")
        st.subheader("备案信息摘要")
        summary_data = {k: v for k, v in submission_data.items() if k not in ['提交用户ID', '提交用户角色']}
        summary_df = pd.DataFrame([summary_data])
        st.dataframe(summary_df, use_container_width=True)
    else:
        st.error("❌ 提交失败，请重试")


def show_my_submissions():
    """显示当前用户的备案记录"""
    st.header("我的备案记录")

    # 根据用户角色决定显示哪些记录
    if st.session_state.user_role == "科研办审核员":
        # 审核员可以看到所有记录
        user_submissions = st.session_state.submissions
        st.write(f"🔍 **审核员视图** - 共 **{len(user_submissions)}** 条备案记录：")
    else:
        # 科研人员只能看到自己的记录
        user_submissions = [s for s in st.session_state.submissions if s.get('提交用户ID') == st.session_state.user_id]
        st.write(f"您共有 **{len(user_submissions)}** 条备案记录：")

    if not user_submissions:
        if st.session_state.user_role == "科研办审核员":
            st.info("暂无任何备案记录")
        else:
            st.info("您还没有提交过备案记录")
        return

    # 转换为DataFrame显示
    display_data = []
    for submission in user_submissions:
        display_item = {
            '备案ID': submission.get('备案ID', ''),
            '论文标题': submission.get('论文标题', ''),
            '第一作者': submission.get('第一作者', ''),
            '目标期刊': submission.get('目标期刊', ''),
            '通讯作者': submission.get('通讯作者', ''),
            '所属科室': submission.get('所属科室', ''),
            '提交时间': submission.get('提交时间', ''),
            '预警状态': submission.get('预警状态', ''),
            '状态': submission.get('状态', ''),
            '审核意见': submission.get('审核意见', '')
        }

        # 如果是审核员，显示提交者信息
        if st.session_state.user_role == "科研办审核员":
            display_item['提交者'] = submission.get('提交用户角色', '未知')

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
        records_df = pd.DataFrame(st.session_state.submissions