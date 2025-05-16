import os
from googleapiclient.http import MediaFileUpload
from .brs_sheets import authenticate_drive
import pdfplumber
import pandas as pd
import os
import re
from tqdm import tqdm

def extract_brs_title(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words(x_tolerance=3, y_tolerance=3)

        if not words:
            return "Judul_Tidak_Ditemukan"

        largest_size = 0
        text_by_size = {}

        for word in words:
            size = word['bottom'] - word['top']
            if size > largest_size:
                largest_size = size
            text_by_size.setdefault(size, []).append(word['text'])

        return " ".join(text_by_size[largest_size])

def is_table_name(text):
    return re.match(r"Tabel\s+\d+[\.]?\s*", text.strip())

def extract_table_names(text):
    lines = text.split("\n")
    return [line.strip() for line in lines if is_table_name(line)]

def is_valid_table(table):
    # Tabel dianggap valid jika:
    # - Ada header
    # - Setidaknya 3 baris total (1 header + ≥2 isi)
    # - Semua baris panjangnya sama
    if not table or len(table) < 3:
        return False
    header_len = len(table[0])
    if header_len < 2:
        return False
    for row in table:
        if len(row) != header_len:
            return False
        if not any(cell and cell.strip() for cell in row):
            return False
    return True

def page_contains_only_images(page):
    # Jika halaman hanya berisi gambar (tanpa teks), kita lewati
    has_text = page.extract_text()
    has_images = page.images
    return not has_text and len(has_images) > 0

def pdf_to_excel(pdf_path):
    try:
        brs_title = extract_brs_title(pdf_path).strip().replace(" ", "_").replace("/", "-")
        output_path = os.path.splitext(pdf_path)[0] + f"_{brs_title}.xlsx"
        sheet_links = []

        with pdfplumber.open(pdf_path) as pdf:
            full_text = "\n".join([p.extract_text() or "" for p in pdf.pages])
            all_table_names = extract_table_names(full_text)

            with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                table_counter = 1
                previous_header = None  # Simpan header sebelumnya

                for i, page in tqdm(enumerate(pdf.pages), total=len(pdf.pages), desc="Memindai Halaman"):
                    if page_contains_only_images(page):
                        continue

                    tables = page.extract_tables()

                    for table in tables:
                        if not is_valid_table(table):
                            continue

                        current_header = table[0]
                        df = pd.DataFrame(table[1:], columns=current_header)
                        if df.empty:
                            continue

                        # Deteksi apakah ini lanjutan dari tabel sebelumnya
                        is_continuation = previous_header == current_header

                        if is_continuation and table_counter > 1:
                            sheet_name = f"Tabel {table_counter - 1} (Lanjutan)"
                            full_table_name = f"Lanjutan Tabel {table_counter - 1}"
                        else:
                            sheet_name = f"Tabel {table_counter}"
                            full_table_name = (
                                all_table_names[table_counter - 1]
                                if table_counter <= len(all_table_names)
                                else sheet_name
                            )
                            table_counter += 1

                        table_info_row = [full_table_name] + [''] * (df.shape[1] - 1)
                        df.loc[len(df)] = table_info_row

                        df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
                        sheet_links.append({"judul_sheet": sheet_name, "gid": None})

                        previous_header = current_header  # Simpan header untuk tabel berikutnya

        return output_path, sheet_links

    except Exception as e:
        raise Exception(f"Gagal konversi PDF ke Excel: {str(e)}")

def convert_to_google_sheets(file_id):
    """
    Mengonversi file Excel (.xlsx) di Google Drive menjadi Google Sheets.
    """
    drive_service = authenticate_drive()

    # Salin file dengan format Google Sheets
    copied_file = drive_service.files().copy(
        fileId=file_id,
        body={"mimeType": "application/vnd.google-apps.spreadsheet"}
    ).execute()

    new_file_id = copied_file["id"]
    new_file_url = f"https://docs.google.com/spreadsheets/d/{new_file_id}/edit"

    print(f"✅ File dikonversi ke Google Sheets: {new_file_url}")

    return new_file_id, new_file_url


def upload_to_drive(file_path, return_id=False):
    """
    Mengunggah file ke Google Drive sebagai .xlsx lalu mengonversinya ke Google Sheets.
    """
    drive_service = authenticate_drive()
    
    file_metadata = {
        'name': os.path.basename(file_path),
    }
    
    media = MediaFileUpload(file_path, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    file_drive = drive_service.files().create(body=file_metadata, media_body=media, fields='id,webViewLink').execute()
    
    file_id = file_drive['id']
    file_url = file_drive['webViewLink']

    print(f"✅ File Excel diunggah ke Google Drive: {file_url}")

    # Konversi ke Google Sheets
    new_file_id, new_file_url = convert_to_google_sheets(file_id)

    # Hapus file Excel asli agar tidak ada duplikasi
    drive_service.files().delete(fileId=file_id).execute()

    # Ubah izin agar file Google Sheets bisa diakses oleh siapa saja (view-only)
    drive_service.permissions().create(
        fileId=new_file_id,
        body={'type': 'anyone', 'role': 'reader'}  # "anyone" berarti public, "reader" berarti view-only
    ).execute()

    return (new_file_url, new_file_id) if return_id else new_file_url


def check_file_type(file_id):
    """
    Memeriksa apakah file di Google Drive adalah Google Sheets atau bukan.
    """
    drive_service = authenticate_drive()
    file_metadata = drive_service.files().get(fileId=file_id, fields="mimeType").execute()
    
    mime_type = file_metadata.get("mimeType", "")
    
    if mime_type == "application/vnd.google-apps.spreadsheet":
        print("✅ File adalah Google Sheets, bisa diakses dengan API.")
        return True
    else:
        print(f"⚠️ File bukan Google Sheets! MIME Type: {mime_type}")
        return False
