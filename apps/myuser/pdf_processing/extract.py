import os
from googleapiclient.http import MediaFileUpload
from .brs_sheets import authenticate_drive
import pdfplumber
import pandas as pd
import os
from tqdm import tqdm

def extract_brs_title(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]  # Ambil halaman pertama
        words = page.extract_words(x_tolerance=3, y_tolerance=3)  # Ekstrak teks
        
        if not words:
            return "Tidak ada teks yang ditemukan"

        # Ambil ukuran font terbesar
        largest_size = 0
        text_by_size = {}

        for word in words:
            size = word['bottom'] - word['top']  # Hitung ukuran font berdasarkan tinggi teks
            
            if size > largest_size:
                largest_size = size  # Simpan ukuran terbesar
            
            # Kelompokkan teks berdasarkan ukuran font
            if size in text_by_size:
                text_by_size[size].append(word['text'])
            else:
                text_by_size[size] = [word['text']]

        # Ambil teks dengan ukuran terbesar
        title_text = " ".join(text_by_size.get(largest_size, []))

        return title_text 


def extract_table_names(page_text):
    """Mendeteksi semua nama tabel dari teks halaman PDF."""
    lines = page_text.split("\n")
    table_names = [line.strip() for line in lines if "Tabel" in line]
    return table_names if table_names else None

def extract_images_from_pdf(pdf_path):
    """Ekstraksi gambar dari PDF menggunakan pdfplumber."""
    images = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for img in page.images:
                images.append(img)  # Menyimpan objek gambar
    return images

def pdf_to_excel(pdf_path):
    """
    Konversi PDF ke Excel dengan pdfplumber dan menyimpan informasi sheet.
    """
    try:
        output_path = pdf_path.replace('.pdf', '.xlsx')
        sheet_links = []  # Untuk menyimpan informasi sheet

        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                for i, page in tqdm(enumerate(pdf.pages), total=total_pages, desc="Ekstraksi PDF", unit="halaman"):
                    tables = page.extract_tables()
                    page_text = page.extract_text() or ""
                    table_names = extract_table_names(page_text) or []

                    images = extract_images_from_pdf(pdf_path)
                    if images:
                        print(f"⚠ Gambar ditemukan di halaman {i+1}, gambar ini akan diabaikan.")
                    
                    if tables:

                        # Hanya ekstrak tabel yang ada, abaikan elemen lain
                        for table_idx, table in enumerate(tables):
                            if table and len(table) > 4:  # Pastikan tabel memiliki lebih dari satu baris (ada data selain header)
                                df = pd.DataFrame(table[1:], columns=table[0])  # Menyusun DataFrame
                                if not df.empty:  # Pastikan DataFrame tidak kosong
                                    sheet_name = table_names[table_idx] if table_idx < len(table_names) else f"Tabel_{i+1}_{table_idx+1}"
                                    sheet_name1 = sheet_name[:8]  # Batasan nama sheet di Excel (maks 31 karakter)
                                    
                                    sheet_name2 = pd.DataFrame([[sheet_name] + [''] * (len(df.columns) - 1)], columns=df.columns)
                                    df_com = pd.concat([df, sheet_name2], ignore_index=True)
                                    df_com.to_excel(writer, sheet_name=sheet_name1, index=False)
                                    sheet_links.append({"judul_sheet": sheet_name1, "gid": None})

        return output_path, sheet_links
    except Exception as e:
        raise Exception(f"Error converting PDF to Excel: {str(e)}")
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
