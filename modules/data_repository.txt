import streamlit as st
import pandas as pd
from modules.loader import load_raw, load_rule
from modules.derivations import derive_columns

class QualityDataRepository:
    def __init__(self, selected_dates, rule_file, raw_dir):
        self.selected_dates = selected_dates
        self.rule_file = rule_file
        self.raw_dir = raw_dir
        self._df = None
        self._code_to_cause = None

    @st.cache_data(ttl=300)
    def _load_base_data(_self, dates, rule_file, raw_dir):
        code_to_cause, _, _ = load_rule(rule_file)
        raw = load_raw(dates, raw_dir)
        if raw.empty:
            return raw, code_to_cause
        df = derive_columns(raw, code_to_cause, {}, {})
        return df, code_to_cause

    def get_full_data(self):
        if self._df is None:
            self._df, self._code_to_cause = self._load_base_data(
                self.selected_dates, self.rule_file, self.raw_dir
            )
        return self._df

    def get_filtered_data(self, types=None, shop=None):
        df = self.get_full_data()
        if types:
            df = df[df["类型"].isin(types)]
        if shop:
            df = df[df["车间"] == shop]
        return df