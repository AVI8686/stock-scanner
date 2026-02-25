import customtkinter as ctk
from tradingview_screener import Query, Column
import webbrowser
import threading
import csv
from datetime import datetime


class ScannerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Technical Scanner 62.0 - MA Touch + Confirm + CSV + Grade")
        self.geometry("1600x950")

        # Header
        self.market_frame = ctk.CTkFrame(self, height=60, fg_color="#2c3e50")
        self.market_frame.pack(fill="x", padx=40, pady=10)
        self.market_label = ctk.CTkLabel(
            self.market_frame,
            text="סורק: נגיעה בממוצע + נר אישור + SMA עולה + CSV + דירוג A/B/C",
            font=("Arial", 18, "bold"),
        )
        self.market_label.pack(pady=15)

        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=20)

        self.scan_p = ctk.CTkFrame(self.content)
        self.scan_p.pack(side="left", fill="both", expand=True, padx=10)

        # Row 0 - trend + interval
        row0 = ctk.CTkFrame(self.scan_p, fg_color="transparent")
        row0.pack(pady=5, fill="x")

        self.trade_v = ctk.StringVar(value="לונג (Uptrend)")
        ctk.CTkOptionMenu(
            row0, values=["לונג (Uptrend)", "שורט (Downtrend)"], variable=self.trade_v
        ).pack(side="right", padx=5)

        ctk.CTkLabel(row0, text="אינטרוול:").pack(side="right", padx=2)
        self.interval_v = ctk.StringVar(value="Daily")
        ctk.CTkOptionMenu(row0, values=["Daily", "Weekly"], variable=self.interval_v).pack(
            side="right", padx=5
        )

        # Row 1 - filters
        row1 = ctk.CTkFrame(self.scan_p, fg_color="transparent")
        row1.pack(pady=10, fill="x")

        self.filters = {}
        self.add_f(row1, "נרות אחורה:", "lb", "15")
        self.add_f(row1, "ממוצע כניסה:", "sma_touch", "150")
        self.add_f(row1, "% סטייה:", "prox", "0.8")
        self.add_f(row1, "ממוצע 2:", "sma2", "200")
        self.add_f(row1, "SMA עולה N:", "rise_n", "10")

        # Row 2 - toggles
        row2 = ctk.CTkFrame(self.scan_p, fg_color="transparent")
        row2.pack(pady=5, fill="x")

        self.require_confirm_v = ctk.StringVar(value="כן")
        ctk.CTkLabel(row2, text="נר אישור:").pack(side="right", padx=2)
        ctk.CTkOptionMenu(row2, values=["כן", "לא"], variable=self.require_confirm_v).pack(
            side="right", padx=5
        )

        self.require_strong_confirm_v = ctk.StringVar(value="כן")
        ctk.CTkLabel(row2, text="אישור חזק (שבירת High/Low):").pack(side="right", padx=2)
        ctk.CTkOptionMenu(row2, values=["כן", "לא"], variable=self.require_strong_confirm_v).pack(
            side="right", padx=5
        )

        self.require_ma_align_v = ctk.StringVar(value="כן")
        ctk.CTkLabel(row2, text="MA150 מעל MA200:").pack(side="right", padx=2)
        ctk.CTkOptionMenu(row2, values=["כן", "לא"], variable=self.require_ma_align_v).pack(
            side="right", padx=5
        )

        self.require_sma_rising_v = ctk.StringVar(value="כן")
        ctk.CTkLabel(row2, text="SMA עולה:").pack(side="right", padx=2)
        ctk.CTkOptionMenu(row2, values=["כן", "לא"], variable=self.require_sma_rising_v).pack(
            side="right", padx=5
        )

        # Buttons
        btn_frame = ctk.CTkFrame(self.scan_p, fg_color="transparent")
        btn_frame.pack(pady=10)

        self.btn_run = ctk.CTkButton(
            btn_frame,
            text="הרץ סריקה",
            fg_color="#27ae60",
            height=45,
            width=200,
            command=self.start_scan,
        )
        self.btn_run.pack(side="left", padx=5)

        self.btn_clear = ctk.CTkButton(
            btn_frame,
            text="נקה תוצאות",
            fg_color="#c0392b",
            height=45,
            command=self.clear_results,
        )
        self.btn_clear.pack(side="left", padx=5)

        self.res_banner = ctk.CTkLabel(
            self.scan_p, text="מוכן", font=("Arial", 16, "bold"), fg_color="#34495e", height=45
        )
        self.res_banner.pack(fill="x", padx=20, pady=5)

        self.progress = ctk.CTkProgressBar(self.scan_p, width=700)
        self.progress.set(0)
        self.progress.pack(pady=5)

        self.results_frame = ctk.CTkScrollableFrame(self.scan_p, height=600)
        self.results_frame.pack(fill="both", expand=True, pady=10)

        self._scan_lock = threading.Lock()
        self._results = []  # for CSV

    # ---------- UI helpers ----------
    def ui(self, fn, *args, **kwargs):
        self.after(0, lambda: fn(*args, **kwargs))

    def add_f(self, p, label, key, default):
        f = ctk.CTkFrame(p, fg_color="transparent")
        f.pack(side="left", padx=10)
        ctk.CTkLabel(f, text=label).pack(side="left")
        e = ctk.CTkEntry(f, width=75)
        e.insert(0, default)
        e.pack(side="left", padx=2)
        self.filters[key] = e

    def clear_results(self):
        for w in self.results_frame.winfo_children():
            w.destroy()
        self._results = []
        self.res_banner.configure(text="תוצאות נמחקו", fg_color="#34495e")
        self.progress.set(0)

    # ---------- CSV ----------
    def save_csv(self, filename="results.csv"):
        if not self._results:
            return
        with open(filename, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "timestamp",
                    "symbol",
                    "ticker",
                    "price",
                    "days_back",
                    "grade",
                    "interval",
                    "touch_sma",
                    "sma2",
                ]
            )
            for r in self._results:
                w.writerow(r)

    # ---------- scan ----------
    def start_scan(self):
        if not self._scan_lock.acquire(blocking=False):
            return
        self.btn_run.configure(state="disabled", text="סורק...")
        self.ui(self.res_banner.configure, text="סורק...", fg_color="#34495e")
        self.ui(self.progress.set, 0)
        threading.Thread(target=self.run_logic, daemon=True).start()

    def grade_signal(self, is_long, touch_dist_pct, strong_confirm):
        """
        A/B/C:
        - A: very close touch (<=0.3%) + strong confirm
        - B: close touch (<=0.8%) or strong confirm
        - C: everything else
        """
        if touch_dist_pct <= 0.3 and strong_confirm:
            return "A"
        if touch_dist_pct <= 0.8 or strong_confirm:
            return "B"
        return "C"

    def run_logic(self):
        try:
            self._results = []
            lb_limit = max(1, int(self.filters["lb"].get()))
            sma_touch = self.filters["sma_touch"].get().strip()
            sma2 = self.filters["sma2"].get().strip()
            prox = float(self.filters["prox"].get()) / 100.0
            rise_n = max(1, int(self.filters["rise_n"].get()))

            is_long = "לונג" in self.trade_v.get()
            require_confirm = self.require_confirm_v.get() == "כן"
            require_strong_confirm = self.require_strong_confirm_v.get() == "כן"
            require_ma_align = self.require_ma_align_v.get() == "כן"
            require_sma_rising = self.require_sma_rising_v.get() == "כן"

            sma_touch_name = f"SMA{sma_touch}"
            sma2_name = f"SMA{sma2}"

            interval_map = {"Daily": "1D", "Weekly": "1W"}
            selected_int = interval_map.get(self.interval_v.get(), "1D")

            q = Query().set_markets("america").where(Column("volume") >= 400000, Column("close") >= 5)

            if hasattr(q, "set_timeframe"):
                try:
                    q = q.set_timeframe(selected_int)
                except Exception:
                    pass

            # trend filter
            if is_long:
                q = q.where(Column("close") > Column(sma_touch_name))
            else:
                q = q.where(Column("close") < Column(sma_touch_name))

            # MA alignment
            if require_ma_align:
                if is_long:
                    q = q.where(Column(sma_touch_name) > Column(sma2_name))
                else:
                    q = q.where(Column(sma_touch_name) < Column(sma2_name))

            # SMA rising
            if require_sma_rising:
                # SMA today > SMA[rise_n]
                sn = f"[{rise_n}]"
                q = q.where(Column(sma_touch_name) > Column(f"{sma_touch_name}{sn}"))

            # Build columns
            need_back = max(lb_limit + 2, rise_n + 1)
            cols = ["name", "close"]
            for i in range(need_back + 1):
                s = f"[{i}]" if i > 0 else ""
                cols.extend(
                    [
                        f"open{s}",
                        f"low{s}",
                        f"high{s}",
                        f"close{s}",
                        f"{sma_touch_name}{s}",
                        f"{sma2_name}{s}",
                    ]
                )

            _, df = q.select(*cols).limit(500).get_scanner_data()

            if df is None or df.empty:
                self.ui(
                    self.res_banner.configure,
                    text="אין תוצאות מהשרת - נסה שוב / שנה סינון",
                    fg_color="#34495e",
                )
                return

            self.ui(self.clear_results)

            total = len(df)
            found = 0

            for idx, row in df.iterrows():
                self.ui(self.progress.set, min(1.0, (idx + 1) / max(1, total)))

                symbol = row.get("name")
                last_price = row.get("close")
                if symbol is None or last_price is None:
                    continue

                start_i = 1 if require_confirm else 0

                for i in range(start_i, lb_limit + 1):
                    s = f"[{i}]" if i > 0 else ""
                    s_conf = f"[{i-1}]" if (i - 1) > 0 else ("" if (i - 1) == 0 else None)
                    s_prev = f"[{i+1}]" if (i + 1) > 0 else ""

                    try:
                        m = row.get(f"{sma_touch_name}{s}")
                        lo = row.get(f"low{s}")
                        hi = row.get(f"high{s}")
                        cl = row.get(f"close{s}")

                        if m is None or lo is None or hi is None or cl is None:
                            continue

                        m = float(m)
                        lo = float(lo)
                        hi = float(hi)
                        cl = float(cl)

                        # touch distance in %
                        if is_long:
                            touch_dist_pct = max(0.0, (lo / m - 1.0) * 100.0)
                            touched = lo <= m * (1.0 + prox)
                        else:
                            touch_dist_pct = max(0.0, (1.0 - hi / m) * 100.0)
                            touched = hi >= m * (1.0 - prox)

                        if not touched:
                            continue

                        # came from right side (support/resistance)
                        prev_close = row.get(f"close{s_prev}")
                        prev_ma = row.get(f"{sma_touch_name}{s_prev}")
                        if prev_close is None or prev_ma is None:
                            continue
                        prev_close = float(prev_close)
                        prev_ma = float(prev_ma)

                        if is_long:
                            came_from_right_side = prev_close > prev_ma
                        else:
                            came_from_right_side = prev_close < prev_ma

                        if not came_from_right_side:
                            continue

                        # confirm candle checks
                        strong_ok = False
                        if require_confirm:
                            if s_conf is None:
                                continue
                            o2 = row.get(f"open{s_conf}")
                            c2 = row.get(f"close{s_conf}")
                            m2 = row.get(f"{sma_touch_name}{s_conf}")
                            hi_touch = hi
                            lo_touch = lo
                            if o2 is None or c2 is None or m2 is None:
                                continue
                            o2 = float(o2)
                            c2 = float(c2)
                            m2 = float(m2)

                            if is_long:
                                basic_ok = c2 > o2 and c2 > m2 and c2 > cl
                                strong_ok = c2 > hi_touch
                            else:
                                basic_ok = c2 < o2 and c2 < m2 and c2 < cl
                                strong_ok = c2 < lo_touch

                            if not basic_ok:
                                continue

                            if require_strong_confirm and not strong_ok:
                                continue
                        else:
                            strong_ok = False

                        grade = self.grade_signal(is_long, abs(touch_dist_pct), strong_ok)
                        self.ui(self.add_result, symbol, float(last_price), i, is_long, sma_touch, sma2, grade)

                        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ticker = symbol.split(":")[-1]
                        self._results.append(
                            [
                                ts,
                                symbol,
                                ticker,
                                float(last_price),
                                i,
                                grade,
                                self.interval_v.get(),
                                f"SMA{sma_touch}",
                                f"SMA{sma2}",
                            ]
                        )

                        found += 1
                        break

                    except Exception:
                        continue

            # save CSV
            self.save_csv("results.csv")

            self.ui(
                self.res_banner.configure,
                text=(
                    f"נמצאו {found} תוצאות | נשמר ל-results.csv | {self.interval_v.get()}"
                    f" | SMA{sma_touch} touch"
                ),
                fg_color="#1e8449" if found > 0 else "#34495e",
            )

        except Exception as e:
            self.ui(self.res_banner.configure, text=f"שגיאה: {str(e)[:150]}", fg_color="#922b21")
        finally:
            self.ui(self.btn_run.configure, state="normal", text="הרץ סריקה")
            self._scan_lock.release()

    def add_result(self, symbol, price, days_back, is_long, sma_touch, sma2, grade):
        circles = {
            0: "⓪",
            1: "①",
            2: "②",
            3: "③",
            4: "④",
            5: "⑤",
            6: "⑥",
            7: "⑦",
            8: "⑧",
            9: "⑨",
            10: "⑩",
            11: "⑪",
            12: "⑫",
            13: "⑬",
            14: "⑭",
            15: "⑮",
        }
        circled = circles.get(days_back, f"({days_back})")

        # Grade color
        if grade == "A":
            bg = "#0b5345" if is_long else "#7b241c"
        elif grade == "B":
            bg = "#145a32" if is_long else "#641e16"
        else:
            bg = "#1d8348" if is_long else "#922b21"

        trend_txt = "✅ Uptrend" if is_long else "🔻 Downtrend"
        f = ctk.CTkFrame(self.results_frame, fg_color=bg)
        f.pack(fill="x", pady=2, padx=5)

        ticker = symbol.split(":")[-1]
        txt = f"{ticker:<8} | {price:>7.2f}$ | נגיעה: {circled} | {grade} | SMA{sma_touch}/SMA{sma2} | {trend_txt}"

        ctk.CTkButton(
            f,
            text=txt,
            anchor="w",
            fg_color="transparent",
            font=("Courier New", 15, "bold"),
            command=lambda t=symbol: webbrowser.open(f"https://www.tradingview.com/chart/?symbol={t}"),
        ).pack(side="left", fill="x", expand=True)


if __name__ == "__main__":
    ScannerApp().mainloop()
