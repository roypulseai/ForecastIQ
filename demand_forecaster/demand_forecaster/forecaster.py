
import pandas as pd
import numpy as np
from .utils import ensure_datetime, week_of_month, period_start, wma, median, explode_events, safe_merge_events
from .promotions import EmpiricalLifts

class AttributeAwareForecaster:
    def __init__(self,
                 method='wma',                     # 'wma' or 'median'
                 attributes=None,                 # e.g., ['region','store','item']
                 horizon_freq='D',                # 'D', 'W', 'M'
                 lookback_config=None,            # dict with 'default' and optional per-attribute overrides
                 use_trends=True,
                 use_promotions=True,
                 use_events=True,
                 date_col='date',
                 target_col='sales',
                 promo_col='promo_flag',
                 discount_col='discount',
                 event_name_col='event_name',
                 week_start='MON',
                 event_lag_days=0):
        self.method = method
        self.attributes = attributes or []
        self.horizon_freq = horizon_freq
        self.lookback_config = lookback_config or {'default': {'D':8,'W':6,'M':5}}
        self.use_trends = use_trends
        self.use_promotions = use_promotions
        self.use_events = use_events
        self.date_col = date_col
        self.target_col = target_col
        self.promo_col = promo_col
        self.discount_col = discount_col
        self.event_name_col = event_name_col
        self.week_start = week_start
        self.event_lag_days = event_lag_days
        self._group_state = {}
        self._fitted = False

    # ----------------- helpers -----------------
    def _resolve_lookback(self, key_tuple):
        # Try exact -> partial -> default
        if isinstance(self.lookback_config, dict):
            if key_tuple in self.lookback_config:
                return self.lookback_config[key_tuple]
            for k, v in self.lookback_config.items():
                if k == 'default': continue
                if isinstance(k, tuple) and key_tuple[:len(k)] == k:
                    return v
        return self.lookback_config.get('default', {'D':8,'W':6,'M':5})

    def _baseline_daily(self, hist, dt, lookback_n):
        dow = dt.dayofweek
        same = hist[(hist[self.date_col].dt.dayofweek==dow) & (hist[self.date_col] < dt)].sort_values(self.date_col)
        values = same.tail(lookback_n)[self.target_col].tolist()
        return wma(values) if self.method=='wma' else median(values)

    def _baseline_weekly(self, hist, week_dt, lookback_n):
        wom_target = int(week_of_month(week_dt, self.week_start))
        start_alias = f'W-{self.week_start}'
        tmp = hist.copy()
        tmp['period_start'] = tmp[self.date_col].dt.to_period(start_alias).dt.start_time
        weekly = tmp.groupby('period_start', as_index=False)[self.target_col].sum()
        weekly['wom'] = weekly['period_start'].apply(lambda x: int(week_of_month(x, self.week_start)))
        weekly_past = weekly[weekly['period_start'] < period_start(week_dt, 'W', self.week_start)]
        same_wom = weekly_past[weekly_past['wom']==wom_target].sort_values('period_start')
        values = same_wom.tail(lookback_n)[self.target_col].tolist()
        base = wma(values) if self.method=='wma' else median(values)
        return base

    def _baseline_monthly(self, hist, month_dt, lookback_n):
        target_month = month_dt.month
        tmp = hist.copy()
        tmp['month_start'] = tmp[self.date_col].dt.to_period('M').dt.start_time
        monthly = tmp.groupby('month_start', as_index=False)[self.target_col].sum()
        monthly_past = monthly[monthly['month_start'] < period_start(month_dt, 'M')]
        monthly_past['month'] = monthly_past['month_start'].dt.month
        same_month = monthly_past[monthly_past['month']==target_month].sort_values('month_start')
        values = same_month.tail(lookback_n)[self.target_col].tolist()
        base = wma(values) if self.method=='wma' else median(values)
        return base

    def _trend_factor(self, hist, dt):
        h = hist[[self.date_col, self.target_col]].copy()
        if h.empty:
            return 1.0
        # weekly
        start_alias = f'W-{self.week_start}'
        w = h.copy(); w['p'] = w[self.date_col].dt.to_period(start_alias)
        weekly = np.nan
        if not w.empty:
            wp = w.groupby('p')[self.target_col].mean().reset_index()
            if len(wp) >= 2 and wp.iloc[-2][self.target_col] not in [0, None, np.nan]:
                weekly = (wp.iloc[-1][self.target_col] - wp.iloc[-2][self.target_col]) / wp.iloc[-2][self.target_col]
        # monthly
        m = h.copy(); m['p'] = m[self.date_col].dt.to_period('M')
        monthly = np.nan
        if not m.empty:
            mp = m.groupby('p')[self.target_col].mean().reset_index()
            if len(mp) >= 2 and mp.iloc[-2][self.target_col] not in [0, None, np.nan]:
                monthly = (mp.iloc[-1][self.target_col] - mp.iloc[-2][self.target_col]) / mp.iloc[-2][self.target_col]
        # yearly
        y = h.copy(); y['p'] = y[self.date_col].dt.to_period('Y')
        yearly = np.nan
        if not y.empty:
            yp = y.groupby('p')[self.target_col].mean().reset_index()
            if len(yp) >= 2 and yp.iloc[-2][self.target_col] not in [0, None, np.nan]:
                yearly = (yp.iloc[-1][self.target_col] - yp.iloc[-2][self.target_col]) / yp.iloc[-2][self.target_col]
        arr = [v for v in [weekly, monthly, yearly] if not pd.isna(v)]
        return 1.0 + float(np.nanmean(arr)) if arr else 1.0

    # ----------------- API -----------------
    def fit(self, sales_df, events_df=None):
        sales_df = ensure_datetime(sales_df, self.date_col)
        self._events_daily = explode_events(events_df, attributes=self.attributes, lag_days=self.event_lag_days) if events_df is not None else None
        merged = safe_merge_events(sales_df, self._events_daily, self.attributes)
        self._group_state = {}
        if self.attributes:
            groups = list(merged.groupby(self.attributes))
        else:
            groups = [(tuple(), merged)]
        for keys, grp in groups:
            key_tuple = keys if isinstance(keys, tuple) else (keys,)
            self._group_state[key_tuple] = {
                'hist': grp.sort_values(self.date_col).copy(),
                'lifts': EmpiricalLifts(grp.rename(columns={self.target_col:'sales'}), target_col='sales',
                                        promo_col=self.promo_col, discount_col=self.discount_col, event_name_col=self.event_name_col)
            }
        self._fitted = True
        return self

    def forecast(self, horizon_dates=None, horizon_start=None, horizon_periods=None, future_plan=None, future_events=None):
        assert self._fitted, "Call fit() first"
        # build horizon index
        if horizon_dates is None:
            if horizon_start is None or horizon_periods is None:
                raise ValueError("Provide horizon_dates or (horizon_start & horizon_periods)")
            start = pd.Timestamp(horizon_start)
            if self.horizon_freq == 'D':
                horizon_dates = pd.date_range(start, periods=int(horizon_periods), freq='D')
            elif self.horizon_freq == 'W':
                s = period_start(start, 'W', self.week_start)
                horizon_dates = pd.date_range(s, periods=int(horizon_periods), freq=f'W-{self.week_start}')
            elif self.horizon_freq == 'M':
                s = period_start(start, 'M')
                horizon_dates = pd.date_range(s, periods=int(horizon_periods), freq='MS')
            else:
                raise ValueError("Unsupported horizon_freq")
        horizon_dates = pd.to_datetime(horizon_dates)

        # prepare future plans & events per group
        if future_plan is not None and len(future_plan)>0:
            future_plan = future_plan.copy()
            future_plan[self.date_col] = pd.to_datetime(future_plan[self.date_col])
        future_events_daily = explode_events(future_events, attributes=self.attributes, lag_days=self.event_lag_days) if future_events is not None else None

        rows = []
        for key, state in self._group_state.items():
            hist = state['hist']
            lifts = state['lifts']
            # subgroup future plan/events
            gp_plan = None
            if future_plan is not None and len(future_plan)>0:
                cond = pd.Series(True, index=future_plan.index)
                for i, a in enumerate(self.attributes):
                    cond &= (future_plan[a] == key[i])
                gp_plan = future_plan[cond].copy()
            gp_events = None
            if future_events_daily is not None and len(future_events_daily)>0:
                cond = pd.Series(True, index=future_events_daily.index)
                for i, a in enumerate(self.attributes):
                    if a in future_events_daily.columns:
                        cond &= (future_events_daily[a] == key[i])
                gp_events = future_events_daily[cond].copy()

            lookback_map = self._resolve_lookback(key)
            look_n = lookback_map.get(self.horizon_freq, 8)

            for dt in horizon_dates:
                # baseline
                if self.horizon_freq == 'D':
                    base = self._baseline_daily(hist, dt, look_n)
                elif self.horizon_freq == 'W':
                    base = self._baseline_weekly(hist, dt, look_n)
                else:
                    base = self._baseline_monthly(hist, dt, look_n)

                if pd.isna(base):
                    # fallback recent average
                    if self.horizon_freq == 'D':
                        base = hist[self.target_col].tail(14).mean()
                    elif self.horizon_freq == 'W':
                        tmp = hist.copy(); tmp['p'] = tmp[self.date_col].dt.to_period(f'W-{self.week_start}').dt.start_time
                        w = tmp.groupby('p', as_index=False)[self.target_col].sum()
                        base = w[self.target_col].tail(6).mean() if len(w)>0 else 0.0
                    else:
                        tmp = hist.copy(); tmp['p'] = tmp[self.date_col].dt.to_period('M').dt.start_time
                        m = tmp.groupby('p', as_index=False)[self.target_col].sum()
                        base = m[self.target_col].tail(6).mean() if len(m)>0 else 0.0

                # trend
                tf = self._trend_factor(hist, dt) if self.use_trends else 1.0

                # planned promo/discount
                promo_flag = 0
                discount = 0.0
                if gp_plan is not None and len(gp_plan)>0:
                    r = gp_plan.loc[gp_plan[self.date_col] == dt]
                    if len(r)>0:
                        promo_flag = int(r.iloc[0][self.promo_col]) if self.promo_col in r.columns else 0
                        discount = float(r.iloc[0][self.discount_col]) if self.discount_col in r.columns else 0.0

                # planned event
                event_name = None
                if gp_events is not None and len(gp_events)>0:
                    ev = gp_events.loc[gp_events['date'] == dt]
                    if len(ev)>0:
                        event_name = ev.iloc[0].get('event_name', None)

                # lifts
                factor = 1.0
                if self.use_promotions or self.use_events:
                    factor = lifts.lift_for(promo_flag=promo_flag if self.use_promotions else 0,
                                            discount_val=discount if self.use_promotions else 0.0,
                                            event_name=event_name if self.use_events else None)
                yhat = max(0.0, float(base * tf * factor))

                row = {'date': dt, 'forecast': yhat, 'trend_factor': float(tf),
                       'promo_flag': promo_flag, 'discount': discount, 'event_name': event_name}
                for i, a in enumerate(self.attributes):
                    row[a] = key[i]
                rows.append(row)

        out = pd.DataFrame(rows).sort_values(self.attributes + ['date'] if self.attributes else ['date']).reset_index(drop=True)
        return out
