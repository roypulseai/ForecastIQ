
import numpy as np
import pandas as pd

class EmpiricalLifts:
    def __init__(self, df, target_col='sales', promo_col='promo_flag', discount_col='discount', event_name_col='event_name'):
        self.df = df.copy()
        self.target_col = target_col
        self.promo_col = promo_col if promo_col in df.columns else None
        self.discount_col = discount_col if discount_col in df.columns else None
        self.event_name_col = event_name_col if event_name_col in df.columns else None
        self._promo_lift = 1.0
        self._discount_beta = 0.0
        self._event_lifts = {}
        self._compute()

    def _compute(self):
        d = self.df.copy()
        # promo ratio
        if self.promo_col:
            base = d[d[self.promo_col]==0][self.target_col].mean()
            promo = d[d[self.promo_col]==1][self.target_col].mean()
            if base and base>0 and not pd.isna(promo):
                self._promo_lift = float(promo/base)
        # discount elasticity
        if self.discount_col:
            dd = d.dropna(subset=[self.target_col, self.discount_col])
            if len(dd) >= 10 and dd[self.discount_col].std() > 0:
                x = dd[self.discount_col].astype(float).values
                y = dd[self.target_col].astype(float).values
                b = np.polyfit(x, y, 1)[0]
                mean_sales = dd[self.target_col].mean()
                if mean_sales and mean_sales>0:
                    self._discount_beta = float(b/mean_sales)
        # event lifts
        if self.event_name_col:
            no_ev = d[d[self.event_name_col].isna()][self.target_col].mean()
            if no_ev and no_ev>0:
                for ev, grp in d.groupby(self.event_name_col):
                    if pd.isna(ev): continue
                    if len(grp) >= 3:
                        self._event_lifts[ev] = float(grp[self.target_col].mean()/no_ev)

    def lift_for(self, promo_flag=None, discount_val=None, event_name=None):
        f = 1.0
        if promo_flag not in [None, 0, False, '0']:
            f *= self._promo_lift
        if discount_val not in [None, 0, 0.0, '0', '0.0', '']:
            try:
                d = float(discount_val)
            except Exception:
                d = 0.0
            f *= (1.0 + self._discount_beta * d)
        if event_name not in [None, '']:
            f *= self._event_lifts.get(event_name, 1.0)
        return float(f)
