from datetime import date
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.io as pio
pio.renderers.default = "browser"
import io
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TrafficGaugePlotter:
    def __init__(self, cloud_utils_class):
        self.cloud_utils = cloud_utils_class

        # Weekday and month names in Danish
        self.weekdays = {
            "Monday": "Mandag", "Tuesday": "Tirsdag", "Wednesday": "Onsdag",
            "Thursday": "Torsdag", "Friday": "Fredag", "Saturday": "Lørdag", "Sunday": "Søndag"
        }
        self.months = {
            "January": "Januar", "February": "Februar", "March": "Marts", "April": "April",
            "May": "Maj", "June": "Juni", "July": "Juli", "August": "August",
            "September": "September", "October": "Oktober", "November": "November", "December": "December"
        }

    # Format a date object to Danish readable string
    def to_danish_date(self, d):
        english = d.strftime("%A, %d. %B %Y")
        for en, dk in self.weekdays.items():
            english = english.replace(en, dk)
        for en, dk in self.months.items():
            english = english.replace(en, dk)
        return english

    # Format label with icon and translated date
    def format_label(self, d, period):
        icon = "🌅" if period == "morning" else "🌇"
        label = "Morgen" if period == "morning" else "Eftermiddag"
        return f"{icon} {self.to_danish_date(d)} {label}"

    # Choose color based on deviation
    def get_color_gradient(self, val):
        if val < -15:
            return "#05f545"
        elif val < -10:
            return "#1abc9c"
        elif val < -5:
            return "#37c477"
        elif val < 5:
            return "#f4f4f4"
        elif val < 10:
            return "#f39c12"
        elif val < 15:
            return "#e67e22"
        else:
            return "#f70525"

    # Choose emoji + text based on deviation
    def get_description(self, val):
        if val < -15:
            return "🚀 Meget hurtigere end normalt"
        elif val < -10:
            return "🚗 Hurtigere end normalt"
        elif val < -5:
            return "👍 En smule hurtigere end normalt"
        elif val < 5:
            return "👌 Omtrent som normalt"
        elif val < 10:
            return "⚠️ En smule langsommere end normalt"
        elif val < 15:
            return "🛑 Langsommere end normalt"
        else:
            return "🪦 Meget langsommere end normalt"

    # Plot gauges for desktop layout
    def plot_gauges(self, morning_prediction_dict, afternoon_prediction_dict):
        try:
            combined = [(d, "morning", v) for d, v in morning_prediction_dict.items()] + \
                    [(d, "afternoon", v) for d, v in afternoon_prediction_dict.items()]
            combined_sorted = sorted(combined, key=lambda x: (x[0], 0 if x[1] == "morning" else 1))
            first_two = combined_sorted[:2]
            remaining_mornings = [x for x in combined_sorted if x[1] == "morning" and x not in first_two][:4]
            remaining_afternoons = [x for x in combined_sorted if x[1] == "afternoon" and x not in first_two][:4]
            all_predictions = first_two + remaining_mornings + remaining_afternoons

            values = [v for _, _, v in all_predictions]
            labels = [self.format_label(d, p) for d, p, _ in all_predictions]

            specs = [
                [None, {"type": "indicator"}, {"type": "indicator"}, None],
                [{"type": "indicator"} for _ in range(4)],
                [{"type": "indicator"} for _ in range(4)]
            ]
            fig = make_subplots(rows=3, cols=4, specs=specs, subplot_titles=[""] * 10)

            for i, (val, label) in enumerate(zip(values, labels)):
                if i == 0:
                    row, col = 1, 2
                elif i == 1:
                    row, col = 1, 3
                elif 2 <= i <= 5:
                    row, col = 2, i - 1
                else:
                    row, col = 3, i - 5

                fig.add_trace(go.Indicator(
                    mode="gauge+number",
                    value=val,
                    title={
                        "text": f"{label}<br><span style='font-size:14px;color:gray'>{self.get_description(val)}</span>",
                        "font": {"size": 17}
                    },
                    number={"suffix": "%", "font": {"size": 28, "color": "#2c3e50"}},
                    gauge={
                        'axis': {'range': [-30, 30], 'tickwidth': 2},
                        'bar': {'color': self.get_color_gradient(val)},
                        'threshold': {'line': {'color': "#34495e", 'width': 2}, 'value': 0},
                        'bgcolor': "#f9f9f9",
                        'bordercolor': "#e0e0e0",
                        'borderwidth': 1
                    }
                ), row=row, col=col)

            fig.update_layout(
                height=960,
                margin=dict(t=140, l=40, r=40, b=40),
                paper_bgcolor='#f0f6ff',
                plot_bgcolor='#f0f6ff',
                font=dict(family="Poppins, Segoe UI, sans-serif", color="#2c3e50")
            )

            buffer = io.BytesIO()
            fig.write_image(buffer, format='png', scale=2)
            logger.info("Successfully created desktop traffic gauge plot.")
            return buffer

        except Exception as e:
            logger.error(f"Error occurred while generating desktop traffic gauge plot: {e}")
            return None

    # Plot gauges for mobile layout (2 per row)
    def plot_gauges_mobile(self, morning_prediction_dict, afternoon_prediction_dict):
        try:
            combined = [(d, "morning", v) for d, v in morning_prediction_dict.items()] + \
                    [(d, "afternoon", v) for d, v in afternoon_prediction_dict.items()]
            combined_sorted = sorted(combined, key=lambda x: (x[0], 0 if x[1] == "morning" else 1))
            all_predictions = combined_sorted[:10]

            values = [v for _, _, v in all_predictions]
            labels = [self.format_label(d, p) for d, p, _ in all_predictions]

            rows = (len(values) + 1) // 2
            specs = [[{"type": "indicator"}, {"type": "indicator"}] for _ in range(rows)]
            fig = make_subplots(rows=rows, cols=2, specs=specs, subplot_titles=[""] * len(values))

            for i, (val, label) in enumerate(zip(values, labels)):
                row = i // 2 + 1
                col = i % 2 + 1

                fig.add_trace(go.Indicator(
                    mode="gauge+number",
                    value=val,
                    title={
                        "text": f"{label}<br><span style='font-size:14px;color:gray'>{self.get_description(val)}</span>",
                        "font": {"size": 16}
                    },
                    number={"suffix": "%", "font": {"size": 26, "color": "#2c3e50"}},
                    gauge={
                        'axis': {'range': [-30, 30], 'tickwidth': 2},
                        'bar': {'color': self.get_color_gradient(val)},
                        'threshold': {'line': {'color': "#34495e", 'width': 2}, 'value': 0},
                        'bgcolor': "#f9f9f9",
                        'bordercolor': "#e0e0e0",
                        'borderwidth': 1
                    }
                ), row=row, col=col)

            fig.update_layout(
                height=350 * rows,
                margin=dict(t=140, l=30, r=30, b=40),
                paper_bgcolor='#f0f6ff',
                plot_bgcolor='#f0f6ff',
                font=dict(family="Poppins, Segoe UI, sans-serif", color="#2c3e50")
            )

            buffer = io.BytesIO()
            fig.write_image(buffer, format='png', scale=2)
            logger.info("Successfully created mobile traffic gauge plot.")
            return buffer

        except Exception as e:
            logger.error(f"Error occurred while generating mobile traffic gauge plot: {e}")
            return None
    
    def plot_and_export_to_gcs(self, morning_prediction_dict, afternoon_prediction_dict, bucket_name, gcs_folder_name):

        # Plot predictions for both desktop and mobile devices
        buffer_desktop = self.plot_gauges(morning_prediction_dict, afternoon_prediction_dict)
        buffer_mobile = self.plot_gauges_mobile(morning_prediction_dict, afternoon_prediction_dict)

        self.cloud_utils.upload_to_gcs(buffer_desktop, bucket_name, gcs_folder_name, 'predictions_desktop', 'png')
        self.cloud_utils.upload_to_gcs(buffer_mobile, bucket_name, gcs_folder_name, 'predictions_mobile', 'png')
