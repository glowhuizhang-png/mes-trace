from pathlib import Path
path = Path('modules/uf.py')
text = path.read_text(encoding='utf-8')
old = """    filtered_display = filtered[show_cols].rename(columns=UF_HEADER_MAP)
    # 将 UF 指标列（RVF ~ LOW）居中显示
    numeric_cols = [UF_HEADER_MAP[c] for c in UF_COLUMNS if UF_HEADER_MAP[c] in filtered_display.columns]
    if numeric_cols:
        styler = filtered_display.style.set_properties(**{\"text-align\": \"center\"}, subset=numeric_cols)
    else:
        styler = filtered_display
    st.dataframe(styler, width='stretch', height=height, hide_index=True)
"""
new = """    filtered_display = filtered[show_cols].rename(columns=UF_HEADER_MAP)
    st.dataframe(filtered_display, width='stretch', height=height, hide_index=True)
"""
if old in text:
    path.write_text(text.replace(old, new), encoding='utf-8')
    print('replaced styler block')
else:
    print('old block not found')
    start = text.find('filtered_display = filtered[show_cols].rename(columns=UF_HEADER_MAP)')
    print('start', start)
    print(text[start:start+400])
