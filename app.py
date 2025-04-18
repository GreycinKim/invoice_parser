import streamlit as st
import pandas as pd

st.title("📦 FedEx & UPS Charge Extractor (CSV/XLSX / Grouped View)")

tab1, tab2 = st.tabs(["FedEx Upload", "UPS Upload"])


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

        # === Pivot Table View ===
        st.markdown("### 📊 Normalized View (One Row Per Shipment)")

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


# ===== FedEx Upload Tab =====
with tab1:
    st.header("📨 Upload FedEx CSV or XLSX")
    fedex_file = st.file_uploader("Upload FedEx File", type=["csv", "xlsx"], key="fedex")

    if fedex_file:
        try:
            if fedex_file.name.endswith(".csv"):
                fedex_df = pd.read_csv(fedex_file)
            elif fedex_file.name.endswith(".xlsx"):
                fedex_df = pd.read_excel(fedex_file, engine="openpyxl")
            else:
                st.error("Unsupported file type.")
                fedex_df = None
        except Exception as e:
            st.error(f"Error reading file: {e}")
            fedex_df = None

        if fedex_df is not None:
            process_fedex(fedex_df)


# ===== UPS Upload Tab =====
with tab2:
    st.header("📦 Upload UPS CSV or XLSX")
    ups_file = st.file_uploader("Upload UPS File", type=["csv", "xlsx"], key="ups")

    if ups_file:
        try:
            if ups_file.name.endswith(".csv"):
                ups_df = pd.read_csv(ups_file)
            elif ups_file.name.endswith(".xlsx"):
                ups_df = pd.read_excel(ups_file, engine="openpyxl")
            else:
                st.error("Unsupported file type.")
                ups_df = None
        except Exception as e:
            st.error(f"Error reading file: {e}")
            ups_df = None

        if ups_df is not None:
            process_ups(ups_df)
