import streamlit as st
import pandas as pd
import sqlalchemy as db
import hashlib
from datetime import datetime
import matplotlib.pyplot as plt
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# --- DATABASE SETUP ---
DB_FILE = "expenses.db"
engine = db.create_engine(f"sqlite:///{DB_FILE}")

# --- PASSWORD HASHING ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

# --- USER AUTHENTICATION ---
def add_userdata(username, password):
    with engine.connect() as conn:
        hashed_password = make_hashes(password)
        conn.execute(db.text("INSERT INTO users(username, password) VALUES(:user, :pass)"),
                     {"user": username, "pass": hashed_password})
        conn.commit()

def login_user(username, password):
    with engine.connect() as conn:
        result = conn.execute(db.text("SELECT password FROM users WHERE username = :user"), {"user": username})
        hashed_pass = result.scalar()
        if hashed_pass:
            return check_hashes(password, hashed_pass)
    return False

# --- EXPENSE MANAGEMENT ---
def add_expense(username, date, category, amount, description):
    with engine.connect() as conn:
        conn.execute(db.text("INSERT INTO expenses(username, expense_date, category, amount, description) VALUES(:user, :date, :cat, :amt, :desc)"),
                     {"user": username, "date": date, "cat": category, "amt": amount, "desc": description})
        conn.commit()

def view_all_expenses(username, is_admin=False):
    with engine.connect() as conn:
        if is_admin:
            query = "SELECT id, username, expense_date, category, amount, description FROM expenses"
            df = pd.read_sql(query, conn)
        else:
            query = "SELECT id, expense_date, category, amount, description FROM expenses WHERE username = :user"
            df = pd.read_sql(query, conn, params={"user": username})
    return df

def get_expense_by_id(expense_id):
    with engine.connect() as conn:
        result = conn.execute(db.text("SELECT * FROM expenses WHERE id = :id"), {"id": expense_id})
        return result.first()

def edit_expense_data(expense_id, date, category, amount, description):
    with engine.connect() as conn:
        conn.execute(db.text("UPDATE expenses SET expense_date=:date, category=:cat, amount=:amt, description=:desc WHERE id=:id"),
                     {"date": date, "cat": category, "amt": amount, "desc": description, "id": expense_id})
        conn.commit()

def delete_data(expense_id):
    with engine.connect() as conn:
        conn.execute(db.text("DELETE FROM expenses WHERE id=:id"), {"id": expense_id})
        conn.commit()

# --- DATA VISUALIZATION ---
def plot_expenses_by_category(df):
    if df.empty:
        return None
    category_summary = df.groupby('category')['amount'].sum()
    fig, ax = plt.subplots()
    category_summary.plot(kind='pie', ax=ax, autopct='%1.1f%%', startangle=90)
    ax.set_ylabel('')
    ax.set_title("Expenses by Category")
    return fig

def plot_expenses_over_time(df):
    if df.empty:
        return None
    df['expense_date'] = pd.to_datetime(df['expense_date'])
    time_summary = df.set_index('expense_date').resample('M')['amount'].sum()
    fig, ax = plt.subplots()
    time_summary.plot(kind='line', ax=ax, marker='o')
    ax.set_title("Monthly Spending")
    ax.set_xlabel("Month")
    ax.set_ylabel("Total Amount")
    plt.grid(True)
    return fig

def plot_bar_chart_by_category(df):
    if df.empty:
        return None
    category_summary = df.groupby('category')['amount'].sum().sort_values(ascending=False)
    fig, ax = plt.subplots()
    category_summary.plot(kind='bar', ax=ax)
    ax.set_title("Spending per Category")
    ax.set_xlabel("Category")
    ax.set_ylabel("Total Amount")
    plt.xticks(rotation=45, ha='right')
    return fig

# --- EXPORT FUNCTIONS ---
def export_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Expenses')
    return output.getvalue()

def export_to_pdf(df, username, is_admin=False):
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    title = "Expense Report"
    if is_admin:
        title = "Full Company Expense Report"
    else:
        title = f"Expense Report for {username}"

    elements.append(Paragraph(title, styles['h1']))
    df_list = [df.columns.values.tolist()] + df.values.tolist()
    table = Table(df_list)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    table.setStyle(style)
    elements.append(table)
    doc.build(elements)
    return output.getvalue()

# --- STREAMLIT APP ---
def main():
    st.set_page_config(page_title="Expense Tracker", page_icon="💰")
    st.title("💰 Personal Expense Tracker")

    # Automatically run create_db.py logic on first run
    try:
        with open(DB_FILE) as f:
            pass
    except FileNotFoundError:
        import subprocess
        subprocess.run(['python', 'create_db.py'], check=True)

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['username'] = ''
        st.session_state['is_admin'] = False

    if not st.session_state['logged_in']:
        st.subheader("Login Section")
        username = st.text_input("Username")
        password = st.text_input("Password", type='password')
        if st.button("Login"):
            if login_user(username, password):
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                if username == 'admin':
                    st.session_state['is_admin'] = True
                st.success(f"Welcome {username}")
                st.rerun()
            else:
                st.warning("Incorrect Username/Password")
    else:
        st.sidebar.subheader(f"Welcome {st.session_state['username']}")
        menu = ["Add Expense", "Summary", "Manage Records"]
        choice = st.sidebar.selectbox("Menu", menu)

        if st.sidebar.button("Logout"):
            st.session_state['logged_in'] = False
            st.session_state['username'] = ''
            st.session_state['is_admin'] = False
            st.rerun()

        if choice == "Add Expense":
            st.subheader("Add a New Expense")
            today = datetime.now().date()
            expense_date = st.date_input("Date of Expense", today)
            categories = ["Food", "Transport", "Shopping", "Bills", "Entertainment", "Other"]
            category = st.selectbox("Category", categories)
            amount = st.number_input("Amount", min_value=0.0, format="%.2f")
            description = st.text_area("Description")

            if st.button("Add Expense"):
                add_expense(st.session_state['username'], expense_date, category, amount, description)
                st.success("Expense added successfully!")

        elif choice == "Summary":
            st.subheader("Expense Summary")
            df = view_all_expenses(st.session_state['username'], st.session_state['is_admin'])
            if not df.empty:
                st.dataframe(df)

                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Expenses by Category (Pie Chart)")
                    fig_pie = plot_expenses_by_category(df)
                    if fig_pie:
                        st.pyplot(fig_pie)
                with col2:
                    st.subheader("Spending per Category (Bar Chart)")
                    fig_bar = plot_bar_chart_by_category(df)
                    if fig_bar:
                        st.pyplot(fig_bar)

                st.subheader("Monthly Spending Trend")
                fig_line = plot_expenses_over_time(df)
                if fig_line:
                    st.pyplot(fig_line)
            else:
                st.info("No expenses recorded yet.")

        elif choice == "Manage Records":
            st.subheader("Manage Your Expenses")
            df = view_all_expenses(st.session_state['username'], st.session_state['is_admin'])

            if not df.empty:
                st.dataframe(df)

                st.markdown("### Export Data")
                col1, col2 = st.columns(2)
                with col1:
                    excel_data = export_to_excel(df)
                    st.download_button(label="📥 Export to Excel", data=excel_data, file_name=f"expenses_{st.session_state['username']}.xlsx")
                with col2:
                    pdf_data = export_to_pdf(df, st.session_state['username'], st.session_state['is_admin'])
                    st.download_button(label="📄 Export to PDF", data=pdf_data, file_name=f"report_{st.session_state['username']}.pdf")

                st.markdown("### Edit or Delete Records")
                expense_ids = df['id'].tolist()
                selected_id = st.selectbox("Select Expense ID to Manage", expense_ids)

                if selected_id:
                    col_edit, col_delete = st.columns([1, 1])
                    with col_edit:
                        if st.button("Edit", key=f"edit_{selected_id}"):
                            st.session_state.edit_id = selected_id
                    with col_delete:
                        if st.button("Delete", key=f"delete_{selected_id}"):
                            delete_data(selected_id)
                            st.success(f"Deleted record with ID: {selected_id}")
                            st.rerun()

                    if 'edit_id' in st.session_state and st.session_state.edit_id == selected_id:
                        expense_to_edit = get_expense_by_id(selected_id)
                        with st.form(key='edit_form'):
                            edit_date = st.date_input("Date", value=pd.to_datetime(expense_to_edit.expense_date))
                            edit_category = st.selectbox("Category", ["Food", "Transport", "Shopping", "Bills", "Entertainment", "Other"], index=["Food", "Transport", "Shopping", "Bills", "Entertainment", "Other"].index(expense_to_edit.category))
                            edit_amount = st.number_input("Amount", value=expense_to_edit.amount)
                            edit_description = st.text_area("Description", value=expense_to_edit.description)

                            if st.form_submit_button("Save Changes"):
                                edit_expense_data(selected_id, edit_date, edit_category, edit_amount, edit_description)
                                st.success(f"Updated record with ID: {selected_id}")
                                del st.session_state.edit_id
                                st.rerun()
            else:
                st.info("No expenses recorded to manage.")

if __name__ == '__main__':
    main()
