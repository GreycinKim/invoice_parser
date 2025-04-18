import streamlit as st
import pandas as pd

st.title("📦 FedEx & UPS Charge Extractor (File Upload)")

tab1, tab2 = st.tabs(["FedEx Upload", "UPS Upload"])


# ====== Universal File Loader ======
def load_uploaded_file(uploaded_file):
    if uploaded_file is None:
        return None

    filename = uploaded_file.name.lower()

    try:
        if filename.endswith(".csv"):
            try:
                return pd.read_csv(uploaded_file, encoding="utf-8")
            except UnicodeDecodeError:
                return pd.read_csv(uploaded_file, encoding="ISO-8859-1")

        elif filename.endswith(".xlsx"):
            return pd.read_excel(uploaded_file, engine="openpyxl")

        else:
            st.error("❌ Unsupported file type. Please upload a .csv or .xlsx file.")
            return None

    except Exception as e:
        st.error(f"❌ Error reading file: {e}")
        return None


# ===== FedEx Parser =====
def process_fedex(df, tracking_col_name="Express or Ground Tracking ID"):
    st.success("✅ FedEx file uploaded successfully!")

    charge_description_cols = [col for col in df.columns if "Tracking ID Charge Description" in col]
    charge_amount_cols = [col for col in df.columns if "Tracking ID Charge Amount" in col]
    charge_description_cols.sort()
    charge_amount_cols.sort()

    rows = []
    for _, row in df.iterrows():
        base = {"Tracking ID": row.get(tracking_col_name, "")}
        for desc_col, amt_col in zip(charge_description_cols, charge_amount_cols):
            desc = row.get(desc_col, "")
            amt = row.get(amt_col, "")
            if pd.notna(desc) and desc != "":
                base[f"{desc} (PL-DZ)"] = amt
        rows.append(base)

    result_df = pd.DataFrame(rows)

    charge_type_options = sorted(
        set(col.replace(" (PL-DZ)", "") for col in result_df.columns if col != "Tracking ID")
    )

    if st.button("Select All Penalties (FedEx)"):
        st.session_state["fedex_selected"] = charge_type_options

    selected_penalties = st.multiselect(
        "Select FedEx Penalty Types to Display",
        options=charge_type_options,
        default=st.session_state.get("fedex_selected", []),
        key="fedex_multiselect"
    )

    if selected_penalties:
        columns_to_show = ["Tracking ID"] + [f"{p} (PL-DZ)" for p in selected_penalties]
        filtered_df = result_df[columns_to_show].dropna(subset=columns_to_show[1:], how="all")

        st.subheader("📊 FedEx Penalty Summary")
        for penalty in selected_penalties:
            col_name = f"{penalty} (PL-DZ)"
            if col_name in result_df.columns:
                count = result_df[col_name].notna().sum()
                try:
                    total = pd.to_numeric(result_df[col_name], errors="coerce").sum()
                    st.markdown(f"- **{penalty}**: {count} tracking ID(s), **${total:.2f}** total")
                except:
                    st.markdown(f"- **{penalty}**: {count} tracking ID(s), total unavailable")

        st.dataframe(filtered_df)


# ===== UPS Parser =====
def process_ups(df):
    st.success("✅ UPS file uploaded successfully!")

    df.columns = df.columns.str.strip()

    charge_col = "Charge Description"
    amount_col = "DTrans Amount"
    df[amount_col] = pd.to_numeric(df[amount_col], errors="coerce")

    base_cols = ["Lead Shipment Number", "Shipment Reference Number 1", charge_col, amount_col]

    if not all(col in df.columns for col in base_cols):
        st.error(f"❌ Missing required columns. Found columns: {df.columns.tolist()}")
        return

    charge_types = sorted(df[charge_col].dropna().unique())

    if st.button("Select All Charges (UPS)"):
        st.session_state["ups_selected"] = charge_types

    selected_charges = st.multiselect(
        "Select UPS Charge Types to Display",
        options=charge_types,
        default=st.session_state.get("ups_selected", []),
        key="ups_multiselect"
    )

    if selected_charges:
        filtered_df = df[df[charge_col].isin(selected_charges)]

        st.subheader("📊 UPS Charge Summary")
        for charge in selected_charges:
            charge_df = filtered_df[filtered_df[charge_col] == charge]
            count = len(charge_df)
            total = pd.to_numeric(charge_df[amount_col], errors="coerce").sum()
            st.markdown(f"- **{charge}**: {count} times, **${total:.2f}** total")

        st.markdown("### 📊 (One Row Per Shipment)")

        pivot_df = filtered_df.pivot_table(
            index=["Lead Shipment Number", "Shipment Reference Number 1"],
            columns=charge_col,
            values=amount_col,
            aggfunc="sum"
        ).reset_index()

        pivot_df.columns.name = None
        pivot_df.columns = [str(col) for col in pivot_df.columns]

        # Add total column
        numeric_cols = pivot_df.columns.difference(["Lead Shipment Number", "Shipment Reference Number 1"])
        pivot_df["Total"] = pivot_df[numeric_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1)

        st.dataframe(pivot_df)


# ===== FedEx Upload =====
with tab1:
    st.header("📨 Upload FedEx File (CSV or XLSX)")
    fedex_file = st.file_uploader("FedEx File", type=["csv", "xlsx"], key="fedex")
    fedex_df = load_uploaded_file(fedex_file)
    if fedex_df is not None:
        process_fedex(fedex_df)


# ===== UPS Upload =====
with tab2:
    st.header("📦 Upload UPS File (CSV or XLSX)")
    ups_file = st.file_uploader("UPS File", type=["csv", "xlsx"], key="ups")
    ups_df = load_uploaded_file(ups_file)
    if ups_df is not None:
        process_ups(ups_df)
