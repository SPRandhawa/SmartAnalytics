import pandas as pd
from django.shortcuts import render
from django.contrib import messages
from .models import UploadedFile
from django.contrib.auth.decorators import login_required

def upload_data(request):
    data_preview = None
    columns = None

    if request.method == "POST":
        file = request.FILES.get('data_file')

        if file:
            # Save file
            uploaded = UploadedFile.objects.create(
                user=request.user,
                file=file
            )

            try:
                # READ FILE USING PANDAS
                if file.name.endswith('.csv'):
                    df = pd.read_csv(file)
                elif file.name.endswith('.xlsx'):
                    df = pd.read_excel(file)
                else:
                    messages.error(request, "Unsupported file format ❌", extra_tags="upload")
                    return render(request, "upload/upload.html")

                # ✅ CORRECT POSITION
                data_preview = df.head(10).values.tolist()
                columns = list(df.columns)

                messages.success(request, "File processed successfully ✅", extra_tags="upload")

            except Exception as e:
                messages.error(request, f"Error: {str(e)} ❌", extra_tags="upload")

        else:
            messages.error(request, "Please select a file ❌", extra_tags="upload")

    return render(request, "upload/upload.html", {
        "data_preview": data_preview,
        "columns": columns
    })
