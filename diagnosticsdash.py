# --- COMBINED LINE GRAPH PROCESSING (TOP 4 + TOTAL) ---
# Only include records that have a valid numeric status (0-4)

df_12_line = df_12[df_12["status_num"].notna()].copy()
df_top_line = df_12_line[df_12_line["user"].isin(top_users)].copy()

month_order = [m.strftime("%b %Y") for m in months_12]

# Monthly counts for Top 4 users
monthly_top_users = (
    df_top_line.groupby(["month", "user"])
    .size()
    .reset_index(name="samples")
)
monthly_top_users["label"] = monthly_top_users["month"].dt.strftime("%b %Y")

# Monthly total across ALL users
monthly_grand_total = (
    df_12_line.groupby("month")
    .size()
    .reset_index(name="samples")
)
monthly_grand_total["user"] = "TOTAL (All Users)"
monthly_grand_total["label"] = monthly_grand_total["month"].dt.strftime("%b %Y")

# Combine
combined_line_data = pd.concat(
    [monthly_top_users, monthly_grand_total],
    ignore_index=True
)

combined_line_data["label"] = pd.Categorical(
    combined_line_data["label"],
    categories=month_order,
    ordered=True
)

legend_order = ["TOTAL (All Users)"] + top_users

fig1 = px.line(
    combined_line_data,
    x="label",
    y="samples",
    color="user",
    category_orders={
        "label": month_order,
        "user": legend_order,
    },
    markers=True,
    title="Monthly Samples (Valid Numeric Status Only)",
)

# Show values only on TOTAL line
fig1.update_traces(
    texttemplate="%{y}",
    textposition="top center",
    selector=dict(name="TOTAL (All Users)")
)

fig1.update_layout(
    xaxis_title="Month",
    yaxis_title="Samples"
)

st.plotly_chart(fig1, use_container_width=True)


st.subheader("Status selection by diagnostician")
cols = st.columns(2)

for i, user in enumerate(top_users):
    user_status = df_top[(df_top["user"] == user) & (df_top["status_num"].isin(STATUS_ORDER))].copy()
    status_counts = (
        user_status.groupby("status_num").size()
        .reset_index(name="count")
        .set_index("status_num")
        .reindex(STATUS_ORDER, fill_value=0)
        .reset_index()
    )

    with cols[i % 2]:
        if status_counts["count"].sum() == 0:
            st.info(f"No valid status values 0-4 for {user}.")
        else:
            fig = px.pie(
                status_counts,
                names="status_num",
                values="count",
                hole=0.35,
                title=f"{user} status selection (%)",
                color="status_num",
                color_discrete_map=STATUS_COLORS,
            )
            fig.update_traces(textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)

st.subheader("Monthly table")
# Rebuild the table source pivot to match the graph's clean structure
table_source = monthly_top_users.pivot_table(index="month", columns="user", values="samples", fill_value=0)
table = table_source.reindex(months_12, fill_value=0)
table.index = table.index.strftime("%b %Y")
st.dataframe(table, use_container_width=True)
