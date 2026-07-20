from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import update_session_auth_hash
from datetime import datetime
from accounts.models import Profile
from .models import UploadedDataset
from data_upload.models import UploadedFile
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import pandas as pd
import json
import os
import re
from google import genai
import traceback
from sklearn.linear_model import LinearRegression
import numpy as np
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from xml.sax.saxutils import escape
from django.shortcuts import redirect

def build_summary_text(df):
    if df is None:
        return "Upload a dataset to generate your first professional report."

    summary_lines = []
    summary_lines.append(f"Rows: {len(df)}")
    summary_lines.append(f"Columns: {', '.join(df.columns.tolist())}")

    if 'Revenue' in df.columns:
        summary_lines.append(f"Revenue total: {df['Revenue'].sum():,.2f}")
    if 'Expense' in df.columns:
        summary_lines.append(f"Expense total: {df['Expense'].sum():,.2f}")
    if 'Tax' in df.columns:
        summary_lines.append(f"Tax total: {df['Tax'].sum():,.2f}")
    if 'Date' in df.columns and 'Revenue' in df.columns:
        summary_lines.append("Date range and revenue trend are available for analysis.")
    if 'Category' in df.columns:
        summary_lines.append("Category breakdown is available for segmentation analysis.")

    return "\n".join(summary_lines)

def normalize_report_data(data):
    if not data:
        return {
            'total_revenue': 0,
            'total_expense': 0,
            'total_tax': 0,
            'net_profit': 0,
            'summary': 'Upload a dataset to generate your first professional report.'
        }

    normalized = {}
    for key, value in data.items():
        if isinstance(value, (np.integer, int)):
            normalized[key] = int(value)
        elif isinstance(value, (np.floating, float)):
            normalized[key] = float(value)
        else:
            normalized[key] = value

    return normalized
def build_ai_insights(df):
    if df is None:
        return [
            "Upload a dataset to generate AI insights.",
            "Review revenue and expense trends to improve planning.",
            "Add more historical data for deeper forecasting.",
        ]

    insights = []
    if 'Revenue' in df.columns and 'Expense' in df.columns:
        revenue_total = float(df['Revenue'].sum())
        expense_total = float(df['Expense'].sum())
        if revenue_total >= expense_total:
            insights.append("Revenue is currently outpacing expenses, which is a strong signal.")
        else:
            insights.append("Expenses are higher than revenue, so cost control should be reviewed.")
    else:
        insights.append("Your dataset contains enough structure for business analysis.")

    if 'Date' in df.columns and 'Revenue' in df.columns:
        df_copy = df.copy()
        df_copy['Date'] = pd.to_datetime(df_copy['Date'], errors='coerce')
        monthly_revenue = df_copy.groupby(df_copy['Date'].dt.to_period('M'))['Revenue'].sum()
        if len(monthly_revenue) >= 2:
            if monthly_revenue.iloc[-1] >= monthly_revenue.iloc[-2]:
                insights.append("Revenue is trending upward across recent periods.")
            else:
                insights.append("Revenue has dipped in the latest period and should be reviewed.")
        else:
            insights.append("More monthly history will improve trend visibility.")
    else:
        insights.append("Add date-based data to uncover seasonal patterns.")

    if 'Category' in df.columns:
        top_category = df.groupby('Category')['Revenue'].sum().idxmax() if 'Revenue' in df.columns else 'N/A'
        insights.append(f"Your strongest category is {top_category}.")
    elif 'Product' in df.columns:
        top_product = df.groupby('Product')['Revenue'].sum().idxmax() if 'Revenue' in df.columns else 'N/A'
        insights.append(f"Your best-selling product is {top_product}.")
    else:
        insights.append("Use category or product data to find your strongest segments.")

    return insights[:3]
def ensure_three_ai_insights(ai_insights, df):
    """Keep AI Insight cards consistent, including values saved in older sessions."""
    insights = []
    for insight in ai_insights or []:
        cleaned_insight = re.sub(r"[*_`]+", "", str(insight)).strip()
        if cleaned_insight:
            insights.append(cleaned_insight)

    for fallback_insight in build_ai_insights(df):
        if len(insights) >= 3:
            break
        insights.append(fallback_insight)

    return insights[:3]
def build_smart_insights(df):

    if df is None or df.empty:
        return [{
            "type": "info",
            "text": "Upload a dataset to see your smart business insights here.",
        }]

    if "Revenue" not in df.columns:
        return [{
            "type": "warning",
            "text": "Add a Revenue column to generate smart business insights.",
        }]

    data = df.copy()
    data["Revenue"] = pd.to_numeric(data["Revenue"], errors="coerce").fillna(0)
    revenue = data["Revenue"].sum()
    insights = []

    if "Expense" in data.columns:
        expenses = pd.to_numeric(data["Expense"], errors="coerce").fillna(0).sum()
        taxes = (
            pd.to_numeric(data["Tax"], errors="coerce").fillna(0).sum()
            if "Tax" in data.columns else 0
        )
        profit = revenue - expenses - taxes
        insights.append({
            "type": "success" if profit >= 0 else "danger",
            "text": (
                f"Net {'profit' if profit >= 0 else 'loss'} is ₹{abs(profit):,.2f}."
            ),
        })

    if "Date" in data.columns:
        data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
        dated_data = data.dropna(subset=["Date"])
        monthly_revenue = dated_data.groupby(dated_data["Date"].dt.to_period("M"))["Revenue"].sum()
        if len(monthly_revenue) >= 2:
            change = monthly_revenue.iloc[-1] - monthly_revenue.iloc[-2]
            direction = "increased" if change >= 0 else "decreased"
            insights.append({
                "type": "success" if change >= 0 else "warning",
                "text": f"Revenue {direction} by ₹{abs(change):,.2f} in the latest month.",
            })

    if "Category" in data.columns:
        category_revenue = data.groupby("Category")["Revenue"].sum().dropna()
        if not category_revenue.empty:
            insights.append({
                "type": "info",
                "text": f"{category_revenue.idxmax()} is your highest-revenue category.",
            })
    elif "Product" in data.columns:
        product_revenue = data.groupby("Product")["Revenue"].sum().dropna()
        if not product_revenue.empty:
            insights.append({
                "type": "info",
                "text": f"{product_revenue.idxmax()} is your best-performing product.",
            })

    if not insights:
        insights.append({
            "type": "info",
            "text": f"Your dataset contains ₹{revenue:,.2f} in recorded revenue.",
        })

    return insights[:3]
def build_analytics_insights(df):
    """Return deterministic metrics for the Analytics Insights cards."""
    insights = {
        "best_product": "Not available",
        "worst_product": "Not available",
        "top_category": "Not available",
        "avg_revenue": "Not available",
        "profit_margin": "Not available",
        "best_month": "Not available",
        "worst_month": "Not available",
    }

    if df is None or df.empty or "Revenue" not in df.columns:
        return insights

    data = df.copy()
    data["Revenue"] = pd.to_numeric(data["Revenue"], errors="coerce").fillna(0)

    insights["avg_revenue"] = f"{data['Revenue'].mean():,.2f}"

    if "Product" in data.columns:
        product_revenue = data.groupby("Product")["Revenue"].sum().dropna()
        if not product_revenue.empty:
            insights["best_product"] = str(product_revenue.idxmax())
            insights["worst_product"] = str(product_revenue.idxmin())

    if "Category" in data.columns:
        category_revenue = data.groupby("Category")["Revenue"].sum().dropna()
        if not category_revenue.empty:
            insights["top_category"] = str(category_revenue.idxmax())

    if "Expense" in data.columns:
        expenses = pd.to_numeric(data["Expense"], errors="coerce").fillna(0).sum()
        taxes = (
            pd.to_numeric(data["Tax"], errors="coerce").fillna(0).sum()
            if "Tax" in data.columns else 0
        )
        revenue = data["Revenue"].sum()
        if revenue:
            insights["profit_margin"] = f"{((revenue - expenses - taxes) / revenue) * 100:.2f}"

    if "Date" in data.columns:
        data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
        dated_data = data.dropna(subset=["Date"])
        if not dated_data.empty:
            monthly_revenue = dated_data.groupby(dated_data["Date"].dt.to_period("M"))["Revenue"].sum()
            if not monthly_revenue.empty:
                insights["best_month"] = str(monthly_revenue.idxmax().strftime("%b %Y"))
                insights["worst_month"] = str(monthly_revenue.idxmin().strftime("%b %Y"))

    return insights
def build_chart_explanations(df):
    """Create short, plain-language explanations for the dashboard charts."""
    if df is None or df.empty or "Revenue" not in df.columns:
        return []

    data = df.copy()
    data["Revenue"] = pd.to_numeric(data["Revenue"], errors="coerce").fillna(0)
    explanations = []

    if "Date" in data.columns:
        data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
        dated_data = data.dropna(subset=["Date"])
        monthly = dated_data.groupby(dated_data["Date"].dt.to_period("M"))["Revenue"].sum()
        if not monthly.empty:
            latest_month = monthly.index[-1].strftime("%b %Y")
            latest_revenue = monthly.iloc[-1]
            text = f"Revenue in {latest_month} was INR {latest_revenue:,.2f}."
            if len(monthly) >= 2:
                change = latest_revenue - monthly.iloc[-2]
                direction = "up" if change >= 0 else "down"
                text += f" This is {direction} by INR {abs(change):,.2f} from the previous month."
            explanations.append({"title": "Sales Over Time", "text": text})

    if "Product" in data.columns:
        products = data.groupby("Product")["Revenue"].sum().dropna()
        if not products.empty:
            explanations.append({
                "title": "Top Products",
                "text": f"{products.idxmax()} is the top product, contributing INR {products.max():,.2f} in revenue.",
            })

    if "Category" in data.columns:
        categories = data.groupby("Category")["Revenue"].sum().dropna()
        if not categories.empty:
            explanations.append({
                "title": "Category Revenue",
                "text": f"{categories.idxmax()} is the leading category with INR {categories.max():,.2f} in revenue.",
            })

    if "Category" in data.columns and "Tax" in data.columns:
        data["Tax"] = pd.to_numeric(data["Tax"], errors="coerce").fillna(0)
        taxes = data.groupby("Category")["Tax"].sum().dropna()
        if not taxes.empty:
            explanations.append({
                "title": "Tax Distribution",
                "text": f"{taxes.idxmax()} has the highest tax amount at INR {taxes.max():,.2f}.",
            })

    return explanations
@login_required
def dashboard(request):
    user = request.user

    # =========================
    # GREETING
    # =========================
    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good Morning ☀️"
    elif hour < 16:
        greeting = "Good Afternoon 🌤️"
    else:
        greeting = "Good Evening 🌙"

    # =========================
    # DEFAULT VALUES
    # =========================
    df = None
    data_preview = None
    columns = None

    total_revenue = 0
    total_expense = 0
    total_tax = 0
    net_profit = 0

    growth_rate = 0
    growth_text = "No data"

    file_name = ""
    upload_time = None
    upload_success_message = (
        "File uploaded successfully" if request.GET.get("uploaded") == "1" else None
    )
    show_upload_section = upload_success_message is not None

    sales_over_time = []
    top_products = []
    category_data = []
    tax_data = []

    insights = build_smart_insights(None)
    analytics_insights = build_analytics_insights(None)
    activities = []
    ai_insights = []
    summary = "Upload a dataset to generate your first professional report."

    # 🔥 FIXED: prevent crash
    prediction = None
    future_predictions = []

    # 🔥 REPORT DATA
    report_data = {
        "total_revenue": 0,
        "total_expense": 0,
        "total_tax": 0,
        "net_profit": 0,
        "summary": "No data available"
    }
     # =========================
    # ✅ ADD THIS PART HERE
    # =========================
    

    latest_file = UploadedFile.objects.filter(user=request.user).last()

    if latest_file:
        file_path = latest_file.file.path

        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith('.xlsx'):
            df = pd.read_excel(file_path)

        data_preview = df.head(10).values.tolist()
        columns = list(df.columns)
    # =========================
    # HANDLE POST (UPLOAD)
    # =========================
    if request.method == "POST":

        profile, created = Profile.objects.get_or_create(user=request.user)

        # 🔵 FILE UPLOAD
        if request.FILES.get('data_file'):
            file = request.FILES['data_file']

            try:
                dataset = UploadedDataset.objects.create(
                    user=request.user,
                    file=file
                )

                file_path = dataset.file.path

                if file.name.endswith('.csv'):
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path)

                columns = df.columns.tolist()
                data_preview = df.values.tolist()

                if all(col in df.columns for col in ['Revenue','Expense','Tax']):
                    total_revenue = df['Revenue'].sum()
                    total_expense = df['Expense'].sum()
                    total_tax = df['Tax'].sum()
                    net_profit = total_revenue - total_expense - total_tax

                summary = build_summary_text(df)

                # 🔥 SAVE REPORT DATA
                report_data = normalize_report_data({
                    "total_revenue": total_revenue,
                    "total_expense": total_expense,
                    "total_tax": total_tax,
                    "net_profit": net_profit,
                    "summary": summary
                })
                request.session['report_data'] = report_data

                # GROWTH
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                    df['Month'] = df['Date'].dt.to_period('M')

                    monthly_revenue = df.groupby('Month')['Revenue'].sum()

                    if len(monthly_revenue) >= 2:
                        current = monthly_revenue.iloc[-1]
                        previous = monthly_revenue.iloc[-2]

                        if previous != 0:
                            growth_rate = ((current - previous) / previous) * 100
                            growth_text = f"{round(growth_rate,2)}% from last month"

                file_name = os.path.basename(dataset.file.name)
                upload_time = dataset.uploaded_at

                # Redirect after saving. The one-time query flag displays the message,
                # then the template removes it from the browser URL for a clean refresh.
                return redirect(f"{reverse('dashboard')}?uploaded=1")

            except Exception as e:
                print("ERROR:", e)
                messages.error(request, "Error processing file ❌", extra_tags="upload")
                show_upload_section = True

        # PROFILE / EMAIL / PASSWORD (UNCHANGED)
        if request.FILES.get('profile_image'):
            profile.image = request.FILES.get('profile_image')
            profile.save()

        if 'remove_photo' in request.POST:
            profile.image.delete(save=True)

        if request.POST.get("new_email"):
            user.email = request.POST.get("new_email")
            user.save()

        if request.POST.get("current_password"):
            current = request.POST.get("current_password")
            new = request.POST.get("new_password")
            confirm = request.POST.get("confirm_password")

            if user.check_password(current) and new == confirm:
                user.set_password(new)
                user.save()
                update_session_auth_hash(request, user)
        # =========================
    # LOAD LAST DATASET
    # =========================
    temporary_dataset = False
    selected_dataset_id = request.GET.get("dataset")
    latest_dataset = None
    df = None

    # Selected dataset
    if selected_dataset_id and selected_dataset_id.isdigit():
        latest_dataset = UploadedDataset.objects.filter(
            user=request.user,
            id=int(selected_dataset_id),
        ).first()
        temporary_dataset = latest_dataset is not None

    # Default dataset
    if latest_dataset is None:
        latest_dataset = UploadedDataset.objects.filter(
            user=request.user
        ).order_by('-uploaded_at').first()

    # =========================
    # DEFAULT VALUES
    # =========================
    file_name = ""
    upload_time = None
    columns = []
    data_preview = []
    total_revenue = 0
    total_expense = 0
    total_tax = 0
    net_profit = 0
    growth_text = "No data"
    summary = "Upload a dataset to generate insights."
    # =========================
    # MAIN LOGIC
    # =========================
    if latest_dataset:

        try:
            file_path = latest_dataset.file.path

            # LOAD FILE
            if latest_dataset.file.name.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)

            # FILE INFO
            file_name = os.path.basename(latest_dataset.file.name)
            upload_time = latest_dataset.uploaded_at

            # BASIC DATA
            if df is not None:
                columns = df.columns.tolist()
                data_preview = df.head(10).values.tolist()

            # KPI CALCULATIONS
            if df is not None and all(col in df.columns for col in ['Revenue', 'Expense', 'Tax']):
                total_revenue = df['Revenue'].sum()
                total_expense = df['Expense'].sum()
                total_tax = df['Tax'].sum()
                net_profit = total_revenue - total_expense - total_tax

            # SUMMARY
            if df is not None:
                summary = build_summary_text(df)

            # =========================
            # GROWTH CALCULATION
            # =========================
            if df is not None and 'Date' in df.columns and 'Revenue' in df.columns:

                try:
                    df_copy = df.copy()

                    df_copy['Date'] = pd.to_datetime(df_copy['Date'], errors='coerce')
                    df_copy = df_copy.dropna(subset=['Date'])

                    df_copy['Month'] = df_copy['Date'].dt.to_period('M')
                    monthly_revenue = df_copy.groupby('Month')['Revenue'].sum()

                    if len(monthly_revenue) >= 2:
                        current = monthly_revenue.iloc[-1]
                        previous = monthly_revenue.iloc[-2]

                        if previous != 0:
                            growth_rate = ((current - previous) / previous) * 100
                            growth_text = f"{round(growth_rate, 2)}% from last month"
                        else:
                            growth_text = "Previous month was zero"
                    else:
                        growth_text = "Not enough data"

                except Exception as e:
                    print("GROWTH ERROR:", e)
                    growth_text = "Error calculating growth"

        except Exception as e:
            print("LOAD ERROR:", e)
    # =========================
    # CHART DATA
    # =========================
    if df is not None:
        insights = build_smart_insights(df)
        analytics_insights = build_analytics_insights(df)

        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df['Month'] = df['Date'].dt.strftime('%b %Y')

            monthly = df.groupby('Month')['Revenue'].sum().reset_index()

            sales_over_time = [
                {"month": row["Month"], "revenue": float(row["Revenue"])}
                for _, row in monthly.iterrows()
            ]

        if 'Product' in df.columns:
            products = df.groupby('Product')['Revenue'].sum().sort_values(ascending=False)

            top_products = [
                {"product": idx, "revenue": float(val)}
                for idx, val in products.items()
            ]

        if 'Category' in df.columns:
            categories = df.groupby('Category')['Revenue'].sum()

            category_data = [
                {"category": idx, "revenue": float(val)}
                for idx, val in categories.items()
            ]

        if 'Category' in df.columns and 'Tax' in df.columns:
            tax_group = df.groupby('Category')['Tax'].sum()

            tax_data = [
                {"category": idx, "tax": float(val)}
                for idx, val in tax_group.items()
            ]

    # =========================
    # AI INSIGHTS
    # =========================
    try:
        if df is not None:
            client = genai.Client()

            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=(
                    "Give exactly 3 short business insights based on this data. "
                    "Put each insight on its own line. Use plain text only: no Markdown, "
                    "asterisks, headings, bullets, or numbering.\n"
                    f"{df.head(5)}"
                )
            )

            text = getattr(response, 'text', None)
            if text:
                ai_insights = [line.strip() for line in text.split("\n") if line.strip()]
            else:
                ai_insights = build_ai_insights(df)
        else:
            ai_insights = build_ai_insights(df)

    except Exception:
        ai_insights = build_ai_insights(df)

    ai_insights = ensure_three_ai_insights(ai_insights, df)
    chart_explanations = build_chart_explanations(df)

    request.session['ai_insights'] = ai_insights
    report_data.update({
        "file_name": file_name or "Not available",
        "uploaded_at": upload_time.strftime("%d %b %Y, %I:%M %p") if upload_time else "Not available",
        "ai_insights": ai_insights,
        "chart_explanations": chart_explanations,
    })
    request.session['report_data'] = normalize_report_data(report_data)
    # =========================
    # 📌 RECENT ACTIVITY
    # =========================
    seen = set()
    activities = []

    datasets = UploadedDataset.objects.filter(user=request.user).order_by('-uploaded_at')

    for data in datasets:

        # 🔹 Extract filename (remove full path)
        activity_file_name = os.path.basename(data.file.name)

        # 🔹 Remove random Django suffix (_abc123)
        if "_" in activity_file_name:
            name_part = activity_file_name.rsplit("_", 1)[0]   # split from RIGHT
            extension = activity_file_name.split(".")[-1]
            clean_name = f"{name_part}.{extension}"
        else:
            clean_name = activity_file_name

        # 🔹 Remove duplicates
        if clean_name not in seen:
            seen.add(clean_name)

            activities.append({
                "text": clean_name,
                "time": data.uploaded_at.strftime("%d %b %Y, %I:%M %p"),
                "id": data.id
            })

    alerts = []

    # BUSINESS ALERTS
    if net_profit < 0:
        alerts.append({"type": "danger", "text": "Net loss detected"})
    elif net_profit > 0:
        alerts.append({"type": "success", "text": "Business is profitable"})

    # GROWTH ALERT
    if growth_rate < 0:
        alerts.append({"type": "warning", "text": "Revenue dropped from last month"})
    elif growth_rate > 10:
        alerts.append({"type": "success", "text": f"Revenue increased by {round(growth_rate,2)}%"})

    # DATA ALERT
    if df is not None:
        if df.isnull().sum().sum() > 0:
            alerts.append({"type": "warning", "text": "Dataset contains missing values"})

    # =========================
    # CONTEXT
    # =========================
    context = {
        'user': user,
        'greeting': greeting,
        'data_preview': data_preview,
        'columns': columns,
        'total_revenue': total_revenue,
        'total_expense': total_expense,
        'total_tax': total_tax,
        'net_profit': net_profit,
        'growth_rate': round(growth_rate, 2),
        'growth_text': growth_text,
        'file_name': file_name,
        'upload_time': upload_time,
        'upload_success_message': upload_success_message,
        'show_upload_section': show_upload_section,
        'temporary_dataset': temporary_dataset,
        'sales_over_time': json.dumps(sales_over_time),
        'top_products': json.dumps(top_products),
        'category_data': json.dumps(category_data),
        'tax_data': json.dumps(tax_data),
        'insights': insights,
        'analytics_insights': analytics_insights,
        'activities': activities,
        'ai_insights': ai_insights,
        'chart_explanations': chart_explanations,
        'summary': summary,
        'prediction': prediction,
        'future_predictions': future_predictions,

    }
    context['alerts'] = alerts
    return render(request, 'dashboard/dashboard.html', context)
    'data_preview': data_preview,
    'columns': columns
# =========================
# PDF DOWNLOAD VIEW (ADDED)
# =========================
def download_report(request):

    report_data = request.session.get('report_data')

    if not report_data:
        return HttpResponse("No report data available ❌")

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="report.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=42,
        leftMargin=42,
        topMargin=42,
        bottomMargin=42,
    )
    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("SmartAnalytics Business Report", styles['Title']))
    content.append(Spacer(1, 12))

    dataset_table = Table([
        ["Dataset", report_data.get("file_name", "Not available")],
        ["Uploaded", report_data.get("uploaded_at", "Not available")],
    ], colWidths=[100, 405])
    dataset_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E2E8F0")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    content.append(dataset_table)
    content.append(Spacer(1, 18))

    content.append(Paragraph("1. Key Metrics", styles['Heading2']))
    metrics_table = Table([
        ["Metric", "Amount"],
        ["Total Revenue", f"INR {float(report_data.get('total_revenue', 0)):,.2f}"],
        ["Total Expense", f"INR {float(report_data.get('total_expense', 0)):,.2f}"],
        ["Total Tax", f"INR {float(report_data.get('total_tax', 0)):,.2f}"],
        ["Net Profit", f"INR {float(report_data.get('net_profit', 0)):,.2f}"],
    ], colWidths=[300, 205])
    metrics_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    content.append(metrics_table)
    content.append(Spacer(1, 18))

    content.append(Paragraph("2. Dataset Summary", styles['Heading2']))
    for summary_line in str(report_data.get("summary", "No summary available.")).splitlines():
        if summary_line.strip():
            content.append(Paragraph(escape(summary_line.strip()), styles['BodyText']))
            content.append(Spacer(1, 5))

    content.append(Spacer(1, 10))
    content.append(Paragraph("3. AI Insights", styles['Heading2']))
    ai_insights = report_data.get("ai_insights") or ["No AI insights available."]
    for number, insight in enumerate(ai_insights, start=1):
        content.append(Paragraph(f"{number}. {escape(str(insight))}", styles['BodyText']))
        content.append(Spacer(1, 7))

    chart_explanations = report_data.get("chart_explanations") or []
    if chart_explanations:
        content.append(Spacer(1, 10))
        content.append(Paragraph("4. Chart Explanations", styles['Heading2']))
        for explanation in chart_explanations:
            content.append(Paragraph(
                f"<b>{escape(str(explanation.get('title', 'Chart')))}:</b> "
                f"{escape(str(explanation.get('text', '')))}",
                styles['BodyText'],
            ))
            content.append(Spacer(1, 7))

    doc.build(content)

    return response
# =========================
# OTHER VIEWS
# =========================

def reports(request):
    report_data = request.session.get('report_data')

    if not report_data:
        if request.user.is_authenticated:
            latest_dataset = UploadedDataset.objects.filter(user=request.user).last()
            if latest_dataset:
                try:
                    file_path = latest_dataset.file.path
                    if latest_dataset.file.name.endswith('.csv'):
                        df = pd.read_csv(file_path)
                    else:
                        df = pd.read_excel(file_path)

                    total_revenue = float(df['Revenue'].sum()) if 'Revenue' in df.columns else 0
                    total_expense = float(df['Expense'].sum()) if 'Expense' in df.columns else 0
                    total_tax = float(df['Tax'].sum()) if 'Tax' in df.columns else 0
                    net_profit = total_revenue - total_expense - total_tax
                    summary = build_summary_text(df)
                    report_data = normalize_report_data({
                        'total_revenue': total_revenue,
                        'total_expense': total_expense,
                        'total_tax': total_tax,
                        'net_profit': net_profit,
                        'summary': summary,
                    })
                    request.session['report_data'] = report_data
                except Exception:
                    report_data = {
                        'total_revenue': 0,
                        'total_expense': 0,
                        'total_tax': 0,
                        'net_profit': 0,
                        'summary': 'Upload a dataset to generate your first professional report.'
                    }
            else:
                report_data = normalize_report_data({
                    'total_revenue': 0,
                    'total_expense': 0,
                    'total_tax': 0,
                    'net_profit': 0,
                    'summary': 'Upload a dataset to generate your first professional report.'
                })
        else:
            report_data = {
                'total_revenue': 0,
                'total_expense': 0,
                'total_tax': 0,
                'net_profit': 0,
                'summary': 'Upload a dataset to generate your first professional report.'
            }

    ai_insights = ensure_three_ai_insights(
        request.session.get('ai_insights'),
        None,
    )

    context = {
        'user': request.user,
        'greeting': 'Reports',
        'total_revenue': report_data['total_revenue'],
        'total_expense': report_data['total_expense'],
        'total_tax': report_data['total_tax'],
        'net_profit': report_data['net_profit'],
        'summary': report_data['summary'],
        'ai_insights': ai_insights,
        'active_section': 'report',
    }
    return render(request, 'dashboard/dashboard.html', context)
def analytics(request):
    return render(request, 'dashboard/analytics.html', {'user': request.user})


def activity(request):
    return HttpResponse("Activity")


# =========================
# DATASET MANAGEMENT VIEWS
# =========================

def delete_dataset(request, dataset_id):
    dataset = get_object_or_404(UploadedDataset, id=dataset_id, user=request.user)

    if request.method != "POST":
        return redirect('dashboard')

    # Remove the stored file and database record together.
    if dataset.file:
        dataset.file.delete(save=False)

    dataset.delete()
    return redirect('dashboard')


def load_dataset(request, dataset_id):
    dataset = get_object_or_404(UploadedDataset, id=dataset_id, user=request.user)

    return redirect(f"{reverse('dashboard')}?dataset={dataset.id}")
