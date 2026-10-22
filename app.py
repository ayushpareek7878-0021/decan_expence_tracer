
import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
from pathlib import Path

st.set_page_config(
    page_title="Decan Expense Tracker",
    page_icon="💰",
    layout="wide"
)

DB_PATH = Path(__file__).resolve().parent / "expenses.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product TEXT NOT NULL,
                purpose TEXT NOT NULL,
                expense_date TEXT NOT NULL,
                payment_mode TEXT NOT NULL,
                notes TEXT DEFAULT '',
                amount REAL NOT NULL,
                who_pay TEXT NOT NULL
            )
        """)


def load_expenses():
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT * FROM expenses ORDER BY expense_date DESC, id DESC",
            conn
        )


def add_expense(product, purpose, expense_date, payment_mode,
                notes, amount, who_pay):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO expenses
            (product, purpose, expense_date, payment_mode, notes, amount, who_pay)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            product, purpose, str(expense_date),
            payment_mode, notes, amount, who_pay
        ))


def update_expense(expense_id, product, purpose, expense_date,
                   payment_mode, notes, amount, who_pay):
    with get_connection() as conn:
        conn.execute("""
            UPDATE expenses
            SET product=?, purpose=?, expense_date=?, payment_mode=?,
                notes=?, amount=?, who_pay=?
            WHERE id=?
        """, (
            product, purpose, str(expense_date),
            payment_mode, notes, amount, who_pay, expense_id
        ))


def delete_expense(expense_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM expenses WHERE id=?", (expense_id,))


initialize_database()

st.title("DECAN | Expense Tracker")
st.caption("Record and manage your business expenses.")

tab1, tab2, tab3 = st.tabs([
    "Add Expense", "Expense History", "Edit / Delete"
])

# ADD EXPENSE
with tab1:
    st.subheader("Add New Expense")

    with st.form("add_expense_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            product = st.text_input("Product *")
            purpose = st.text_input("Purpose *")
            expense_date = st.date_input("Date", value=date.today())
            amount = st.number_input(
                "Amount (₹) *",
                min_value=0.01,
                value=100.0,
                step=100.0
            )

        with col2:
            payment_mode = st.selectbox(
                "Payment Mode",
                ["Cash", "UPI", "Bank Transfer", "Other"]
            )
            who_pay = st.text_input("Who Pay / Paid To *")
            notes = st.text_area("Notes")

        submitted = st.form_submit_button(
            "Add Expense",
            use_container_width=True
        )

        if submitted:
            if not product.strip():
                st.error("Product name likho.")
            elif not purpose.strip():
                st.error("Purpose likho.")
            elif not who_pay.strip():
                st.error("Kisko paise diye, uska naam likho.")
            else:
                add_expense(
                    product.strip(),
                    purpose.strip(),
                    expense_date,
                    payment_mode,
                    notes.strip(),
                    amount,
                    who_pay.strip()
                )
                st.success("Expense successfully save ho gaya!")
                st.rerun()

# MONTHLY EXPENSES
st.subheader("Monthly Expenses")

df_monthly = load_expenses()

if not df_monthly.empty:
    df_monthly["Month"] = pd.to_datetime(
        df_monthly["expense_date"]
    ).dt.strftime("%Y-%m")

    monthly_total = df_monthly.groupby("Month")["amount"].sum()

    st.dataframe(
        monthly_total.reset_index().rename(columns={
            "Month": "Month",
            "amount": "Total Expense (₹)"
        }),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Abhi koi expense nahi hai.")

# EXPENSE HISTORY
with tab2:
    st.subheader("All Expenses")

    df = load_expenses()

    if not df.empty:
        search = st.text_input(
            "Search by product, purpose or person",
            key="history_search"
        )

        filtered = df.copy()

        if search.strip():
            mask = filtered[
                ["product", "purpose", "who_pay", "payment_mode", "notes"]
            ].fillna("").astype(str).apply(
                lambda column: column.str.contains(
                    search.strip(), case=False, regex=False
                )
            ).any(axis=1)

            filtered = filtered[mask]

        display_df = filtered.rename(columns={
            "id": "ID",
            "product": "Product",
            "purpose": "Purpose",
            "expense_date": "Date",
            "payment_mode": "Payment Mode",
            "notes": "Notes",
            "amount": "Amount (₹)",
            "who_pay": "Who Pay"
        })

        st.dataframe(
            display_df[
                ["ID", "Product", "Purpose", "Date", "Payment Mode",
                 "Notes", "Amount (₹)", "Who Pay"]
            ],
            use_container_width=True,
            hide_index=True
        )

        st.markdown(f"### Total Expenses: ₹{filtered['amount'].sum():,.2f}")

        csv_data = filtered.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Download Expenses CSV",
            data=csv_data,
            file_name="decan_expenses.csv",
            mime="text/csv"
        )
    else:
        st.info("Abhi koi expense add nahi hua hai.")

# MONTHLY EXCEL DOWNLOAD
st.subheader("Download Monthly Expenses")

df_excel = load_expenses()

if not df_excel.empty:

    df_excel["expense_date"] = pd.to_datetime(df_excel["expense_date"])

    df_excel["Month"] = df_excel["expense_date"].dt.strftime("%Y-%m")

    months = sorted(df_excel["Month"].unique(), reverse=True)

    selected_month = st.selectbox(
        "Select Month",
        months
    )

    monthly_data = df_excel[
        df_excel["Month"] == selected_month
    ].copy()

    monthly_data = monthly_data.drop(columns=["id", "Month"])

    monthly_data = monthly_data.rename(columns={
        "product": "Product",
        "purpose": "Purpose",
        "expense_date": "Date",
        "payment_mode": "Payment Mode",
        "notes": "Notes",
        "amount": "Amount (₹)",
        "who_pay": "Who Pay"
    })

    st.write(f"Total Expenses: ₹{monthly_data['Amount (₹)'].sum():,.2f}")

    import io

    excel_file = io.BytesIO()

    with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
        monthly_data.to_excel(
            writer,
            index=False,
            sheet_name="Monthly Expenses"
        )

    st.download_button(
        label="Download Excel",
        data=excel_file.getvalue(),
        file_name=f"Decan_Expenses_{selected_month}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("Pehle expenses add karo.")        

# EDIT / DELETE
with tab3:
    st.subheader("Edit or Delete Expense")

    df = load_expenses()

    if not df.empty:
        selected_id = st.selectbox(
            "Select Expense",
            df["id"].tolist(),
            format_func=lambda x: (
                f"ID {x} | "
                f"{df.loc[df['id'] == x, 'product'].iloc[0]} | "
                f"₹{df.loc[df['id'] == x, 'amount'].iloc[0]:,.2f}"
            )
        )

        row = df.loc[df["id"] == selected_id].iloc[0]

        st.markdown("#### Edit Expense")

        with st.form("edit_expense_form"):
            col1, col2 = st.columns(2)

            with col1:
                edit_product = st.text_input(
                    "Product", value=row["product"], key="ep"
                )
                edit_purpose = st.text_input(
                    "Purpose", value=row["purpose"], key="eu"
                )
                edit_date = st.date_input(
                    "Date",
                    value=date.fromisoformat(row["expense_date"]),
                    key="ed"
                )
                edit_amount = st.number_input(
                    "Amount (₹)",
                    min_value=0.01,
                    value=float(row["amount"]),
                    step=100.0,
                    key="ea"
                )

            with col2:
                modes = ["Cash", "UPI", "Bank Transfer", "Other"]
                current_mode = row["payment_mode"]
                mode_index = modes.index(current_mode) if current_mode in modes else 0

                edit_mode = st.selectbox(
                    "Payment Mode", modes, index=mode_index, key="em"
                )
                edit_who = st.text_input(
                    "Who Pay / Paid To", value=row["who_pay"], key="ew"
                )
                edit_notes = st.text_area(
                    "Notes", value=row["notes"] or "", key="en"
                )

            save_changes = st.form_submit_button(
                "Save Changes", use_container_width=True
            )

            if save_changes:
                if not edit_product.strip() or not edit_purpose.strip() or not edit_who.strip():
                    st.error("Product, Purpose aur Who Pay fill karo.")
                else:
                    update_expense(
                        selected_id,
                        edit_product.strip(),
                        edit_purpose.strip(),
                        edit_date,
                        edit_mode,
                        edit_notes.strip(),
                        edit_amount,
                        edit_who.strip()
                    )
                    st.success("Expense update ho gaya!")
                    st.rerun()

        st.divider()
        st.markdown("#### Delete Expense")

        confirm = st.checkbox(
            f"Main Expense ID {selected_id} ko delete karna chahta hoon.",
            key="confirm_delete"
        )

        if st.button("Delete Selected Expense", type="primary"):
            if confirm:
                delete_expense(selected_id)
                st.success("Expense delete ho gaya!")
                st.rerun()
            else:
                st.warning("Delete karne se pehle confirmation select karo.")

    else:
        st.info("Edit ya delete karne ke liye pehle expense add karo.")

# Custom CSS
st.markdown("""
<style>
/* Main background */
.stApp {
    background: linear-gradient(135deg, #080808, #111418);
    color: #f5f5f5;
}

/* Main content */
.block-container {
    max-width: 1250px;
    padding-top: 2rem;
    padding-bottom: 2rem;
}

/* Headings */
h1 {
    color: #ffffff !important;
    font-size: 34px !important;
    font-weight: 700 !important;
    letter-spacing: -1px;
}

h2, h3 {
    color: #f2f2f2 !important;
    font-weight: 600 !important;
}

/* Input fields */
.stTextInput input,
.stNumberInput input,
.stDateInput input,
.stTextArea textarea {
    background-color: #171a1f !important;
    color: white !important;
    border: 1px solid #30343a !important;
    border-radius: 8px !important;
}

/* Dropdowns */
.stSelectbox div[data-baseweb="select"] > div {
    background-color: #171a1f !important;
    color: white !important;
    border-color: #30343a !important;
    border-radius: 8px !important;
}

/* Buttons */
.stButton button,
.stFormSubmitButton button {
    background: #f1f1f1 !important;
    color: #111111 !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    min-height: 42px;
    transition: 0.2s ease;
}

.stButton button:hover,
.stFormSubmitButton button:hover {
    background: #d4d4d4 !important;
    border: none !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 12px;
    border-bottom: 1px solid #30343a;
}

.stTabs [data-baseweb="tab"] {
    color: #b7bbc2;
    font-weight: 500;
}

.stTabs [aria-selected="true"] {
    color: white !important;
}

/* Data table */
[data-testid="stDataFrame"] {
    border: 1px solid #30343a;
    border-radius: 10px;
    overflow: hidden;
}

/* Metrics and bordered containers */
[data-testid="stMetric"],
[data-testid="stForm"] {
    background: #111418;
    border: 1px solid #292e34;
    border-radius: 10px;
    padding: 16px;
}

/* Labels */
label, .stMarkdown p {
    color: #dedede;
}

/* Dividers */
hr {
    border-color: #292e34;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0b0d10;
    border-right: 1px solid #292e34;
}

/* Success and error messages */
[data-testid="stAlert"] {
    border-radius: 8px;
}

/* Remove excessive top whitespace */
header[data-testid="stHeader"] {
    background: transparent;
}
</style>
""", unsafe_allow_html=True)



