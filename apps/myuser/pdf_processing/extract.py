import os
from googleapiclient.http import MediaFileUpload
from .brs_sheets import authenticate_drive
import pdfplumber
import pandas as pd
import os
import re
from tqdm import tqdm

# import cv2
# from doclayout_yolo import YOLOv10
# from pdf2image import convert_from_path
# import pytesseract
# import os
# import re
# from thefuzz import fuzz # Pastikan sudah pip install thefuzz python-Levenshtein

# import cv2
# from doclayout_yolo import YOLOv10
# from pdf2image import convert_from_path
# import pytesseract
# import re
# import os

# # --- STEP 1: Konversi PDF ke gambar ---
# def pdf_to_images(pdf_path, dpi=300):
#     return convert_from_path(pdf_path, dpi=dpi)

# # --- STEP 2: Ekstrak teks berdasarkan bounding box YOLO ---
# def extract_description_namatabel_from_pdf(pdf_path):
#     model_path = r"C:\Data\Kuliah\Projek_SAD\statsync\apps\myuser\pdf_processing\doclayout_yolo_docstructbench_imgsz1024.pt"
#     pages = pdf_to_images(pdf_path)
#     extracted_data = []

#     for page_num, page in enumerate(pages):
#         img_path = f"temp_page_{page_num}.jpg"
#         page.save(img_path, "JPEG")

#         img = cv2.imread(img_path)
#         model = YOLOv10(model_path)
#         results = model(img)


#         # urutkan hasil berdasarkan posisi y (top to bottom)
#         boxes = sorted(results[0].boxes.data.tolist(), key=lambda x: x[1])  

#         for box in boxes:
#             x1, y1, x2, y2, score, cls_id = box
#             crop = img[int(y1):int(y2), int(x1):int(x2)]
#             text = pytesseract.image_to_string(crop, lang="ind")

#             # regex parser → misah nama tabel
#             if re.search(r'(?i)tabel\s+\d+', text.strip()):
#                 extracted_data.append({"type": "table_name", "content": text.strip()})
#             else:
#                 extracted_data.append({"type": "plain_text", "content": text.strip()})

#         os.remove(img_path)

#     return extracted_data


# # ASLIIIIreeaall
# # --- FUNGSI HELPER UNTUK LOGIKA SKENARIO ANDA ---
# # Di dalam file extract.py

# def _associate_text_with_tables(sorted_elements):
#     """
#     Fungsi internal untuk memproses elemen yang sudah diurutkan dan
#     mengasosiasikan deskripsi (HANYA teks di atas) dengan setiap tabel.
#     """
#     processed_data = []
    
#     title_indices = [i for i, el in enumerate(sorted_elements) if el['type'] == 'Nama_Tabel']

#     for i, title_idx in enumerate(title_indices):
#         title_element = sorted_elements[title_idx]
        
#         # Skenario 2 (diperbarui): Ambil deskripsi HANYA dari teks di atas judul
#         description_above = ""
#         # Cek apakah elemen sebelumnya ada dan merupakan 'plain text'
#         if title_idx > 0 and sorted_elements[title_idx - 1]['type'] == 'plain text':
#             description_above = sorted_elements[title_idx - 1]['text']

#         # Bagian untuk mengambil deskripsi di bawah tabel TELAH DIHAPUS

#         processed_data.append({
#             "title_v2": title_element['text'],
#             "description": description_above.strip(), # Hanya gunakan deskripsi atas
#             "page_num": title_element['page_num'],
#         })
        
#     return processed_data


# # realasliii
# # # --- FUNGSI UTAMA YANG DIPERBARUI ---
# def extract_pdf_layout_data(pdf_path, model_path, debug_output_dir=None):
#     """
#     Fungsi utama untuk mengekstrak data dari PDF.
#     Jika debug_output_dir diisi, fungsi akan menyimpan gambar hasil anotasi.
#     """
#     try:
#         model = YOLOv10(model_path)
#     except Exception as e:
#         raise Exception(f"Gagal memuat model YOLOv10 dari {model_path}: {e}")

#     # Definisikan palet warna untuk visualisasi debug
#     color_map = {
#         "plain text": (255, 182, 193),  # Pink
#         "title": (0, 0, 255),           # Merah
#         "Nama_Tabel": (255, 0, 0),      # Biru (BGR format)
#         "table": (0, 255, 0),           # Hijau
#         "unknown": (128, 128, 128)      # Abu-abu
#     }

#     all_page_elements = []
    
#     try:
#         pages = convert_from_path(pdf_path, dpi=300)
#     except Exception as e:
#         raise Exception(f"Gagal mengonversi PDF. Pastikan poppler terinstal: {e}")

#     for page_num, page in enumerate(pages):
#         img_path = f"temp_page_{page_num}.jpg"
#         page.save(img_path, "JPEG")
#         img = cv2.imread(img_path)

#         det_res = model.predict(img_path, imgsz=1024, conf=0.2, device="cpu")
#         results = det_res[0]
#         class_names = results.names

#         # table_boxes = []
#         # for box in results.boxes:
#         #     if class_names[int(box.cls[0])] == "table":
#         #         table_boxes.append(tuple(map(int, box.xyxy[0])))

#         # Sama seperti GColab: kumpulkan dulu semua box 'table'
#         table_boxes = []
#         for box in results.boxes:
#             if class_names.get(int(box.cls[0])) == "table":
#                 table_boxes.append(tuple(map(int, box.xyxy[0])))

#         page_elements_this_page = []

#         # Loop utama untuk memproses setiap box
#         for box in results.boxes:
#             x1, y1, x2, y2 = map(int, box.xyxy[0])
#             cls = int(box.cls[0])
#             conf = float(box.conf[0])
#             label = class_names.get(cls, 'unknown')
            
#             # Ekstrak teks dari bounding box
#             roi = img[y1:y2, x1:x2]
#             text = pytesseract.image_to_string(roi, lang="ind").strip()

#             # --- ATURAN POST-PROCESSING YANG DISAMAKAN DENGAN GCOLAB ---
#             # Menggunakan text hasil OCR sebagai fallback, mirip dengan `getattr` di GColab
#             if "tabel" in label.lower() or "tabel" in text.lower():
#                 for (tx1, ty1, tx2, ty2) in table_boxes:
#                     if y2 <= ty1 and abs(ty1 - y2) < 80:
#                         label = "Nama_Tabel"
#                         break
#             # --- AKHIR ATURAN ---

#             page_elements_this_page.append({
#                 'type': label, 'text': text, 'box': (x1, y1, x2, y2),
#                 'page_num': page_num, 'conf': conf
#             })

#         # Menambahkan semua elemen dari halaman ini ke daftar utama
#         all_page_elements.extend(page_elements_this_page)

#         # Logika debug untuk menggambar kotak (tidak diubah)
#         if debug_output_dir:
#             debug_image = img.copy()
#             for el in page_elements_this_page: # Menggambar dari elemen halaman ini
#                 x1, y1, x2, y2 = el['box']
#                 label, conf = el['type'], el.get('conf', 0.0)
#                 color = color_map.get(label, color_map["unknown"])
#                 cv2.rectangle(debug_image, (x1, y1), (x2, y2), color, 3)
#                 cv2.putText(debug_image, f"{label} {conf:.2f}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
#             pdf_filename = os.path.basename(pdf_path)
#             debug_filename = f"{os.path.splitext(pdf_filename)[0]}_page_{page_num + 1}_annotated.jpg"
#             output_path = os.path.join(debug_output_dir, debug_filename)
#             cv2.imwrite(output_path, debug_image)
#             print(f"DEBUG: Gambar anotasi disimpan di {output_path}")

#         os.remove(img_path)

#     # Urutkan semua elemen dari semua halaman
#     sorted_elements = sorted(all_page_elements, key=lambda e: (e['page_num'], e['box'][1]))
    
#     # Hapus duplikasi dengan prioritas (jika masih diperlukan, tapi kita sederhanakan dulu)
#     # Untuk saat ini, kita ikuti alur GColab yang tidak memiliki de-duplikasi eksplisit
    
#     final_structured_data = _associate_text_with_tables(sorted_elements)
    
#     return final_structured_data

# ---batass----
    #     # Buat salinan gambar untuk digambari jika mode debug aktif
    #     debug_image = img.copy() if debug_output_dir else None

    #     for box in results.boxes:
    #         x1, y1, x2, y2 = map(int, box.xyxy[0])
    #         cls = int(box.cls[0])
    #         conf = float(box.conf[0])
    #         label = class_names[cls]

    #         if "tabel" in label.lower() or "title" in label.lower():
    #             for (tx1, ty1, tx2, ty2) in table_boxes:
    #                 if y2 <= ty1 and abs(ty1 - y2) < 80:
    #                     label = "Nama_Tabel"
    #                     break

    #         text = ""
    #         if label != "table":
    #             try:
    #                 roi = img[y1:y2, x1:x2]
    #                 text = pytesseract.image_to_string(roi, lang="ind").strip()
    #             except Exception:
    #                 text = ""

    #         if label in ["Nama_Tabel", "plain text", "table", "title"]:
    #             all_page_elements.append({
    #                 'type': label,
    #                 'text': text,
    #                 'box': (x1, y1, x2, y2),
    #                 'page_num': page_num
    #             })
            
    #         # Jika mode debug aktif, gambar kotak di salinan gambar
    #         if debug_image is not None:
    #             color = color_map.get(label, color_map["unknown"])
    #             cv2.rectangle(debug_image, (x1, y1), (x2, y2), color, 3)
    #             cv2.putText(debug_image, f"{label} {conf:.2f}", (x1, y1 - 10),
    #                         cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    #     # Simpan gambar debug jika path diberikan
    #     if debug_image is not None:
    #         # Buat nama file unik berdasarkan nama file asli PDF
    #         pdf_filename = os.path.basename(pdf_path)
    #         debug_filename = f"{os.path.splitext(pdf_filename)[0]}_page_{page_num + 1}_annotated.jpg"
    #         output_path = os.path.join(debug_output_dir, debug_filename)
    #         cv2.imwrite(output_path, debug_image)
    #         print(f"DEBUG: Gambar anotasi disimpan di {output_path}")

    #     os.remove(img_path)

    # sorted_elements = sorted(all_page_elements, key=lambda e: (e['page_num'], e['box'][1]))
    # final_structured_data = _associate_text_with_tables(sorted_elements)
    
    # return final_structured_data

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
    
def get_file_size(file_path):
    size_bytes = os.path.getsize(file_path)
    size_mb = size_bytes / (1024 * 1024)
    return f"{size_mb:.2f} MB"

def get_page_count(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        return len(pdf.pages)

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

# def is_image_title(text):
#     return re.match(r"Gambar\s+\d+[\.]?\s*", text.strip())

# def extract_image_titles(text):
#     lines = text.split("\n")
#     return [line.strip() for line in lines if is_image_title(line)]

def page_contains_only_images(page):
    # Jika halaman hanya berisi gambar (tanpa teks), kita lewati
    has_text = page.extract_text()
    has_images = page.images
    return not has_text and len(has_images) > 0

# def extract_character_colors(pdf_path):
#     with pdfplumber.PDF(pdf_path) as file:
#         for char in file.chars:
#             if char['text'] != ' ':
#                 print(f"Page Number: {char['page_number']}")
#                 print(f"Character: {char['text']}")
#                 print(f"Font Name: {char['fontname']}")
#                 print(f"Font Size: {char['size']}")
#                 print(f"Stroking Color: {char['stroking_color']}")
#                 print(f"Non_stroking Color: {char['non_stroking_color']}")
#                 print('\n')
                

# def is_subheader_title(char):
#     """
#     Deteksi apakah suatu kata/frasa bisa dikategorikan sebagai subheader.
#     Ciri-ciri:
#     1. Warna font bukan hitam (non_stroking_color bukan (0, 0, 0)).
#     2. Ada huruf kapital di tiap kata.
#     3. Biasanya mengandung angka atau tanda titik (opsional).
#     4. Ukuran font sedikit lebih besar dari rata-rata teks deskripsi.
#     """
#     text = char.get("text", "").strip()
#     font_size = char.get("size", 0)
#     # stroke_color = word.get("stroking_color")
#     fill_color = char.get("non_stroking_color")

#     if not text or len(text.split()) < 1:
#         return False

#     # 1️⃣ Warna font bukan hitam
#     is_colored = fill_color not in [None, 0, (0, 0, 0)]

#     # 2️⃣ Setiap kata memiliki huruf kapital
#     capitalized_words = sum(1 for w in text.split() if w and w[0].isupper())
#     is_capitalized = capitalized_words >= len(text.split()) / 2

#     # 3️⃣ Ada angka atau tanda titik (kadang keduanya tidak ada)
#     has_number_or_dot = bool(re.search(r"[\d\.]", text))

#     # Gabungkan kriteria
#     # if is_colored or is_capitalized or has_number_or_dot:
#     #     return True

#     if (is_colored or is_capitalized or has_number_or_dot) and font_size > 0:
#         return True

#     return False

# def extract_subheader_titles(pdf_path):
#     """
#     Ekstrak seluruh teks yang dianggap sebagai subheader dari PDF.
#     Menentukan ukuran font rata-rata teks deskripsi untuk pembanding.
#     """
#     subheaders = []
#     font_sizes = []
#     # fill_colors = []

#     with pdfplumber.open(pdf_path) as pdf:
#         for page in pdf.pages:
#             # Ambil semua karakter (lebih presisi dari extract_words)
#             chars = page.chars
#             if not chars:
#                 continue

#             # Kumpulkan ukuran font rata-rata
#             font_sizes.extend([float(c.get("size", 0)) for c in chars])

#             # Gabungkan karakter menjadi kata berdasarkan posisi Y (baris)
#             words = page.extract_words(x_tolerance=3, y_tolerance=3)
#             for w in words:
#                 if is_subheader_title(w):
#                     subheaders.append(w["text"].strip())

#     # Hitung rata-rata ukuran font semua teks
#     avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 0

#     # Filter: hanya ambil subheader yang punya ukuran font di atas rata-rata deskripsi
#     final_subheaders = []
#     with pdfplumber.open(pdf_path) as pdf:
#         for page in pdf.pages:
#             words = page.extract_words(x_tolerance=3, y_tolerance=3, keep_blank_chars=False)
#             for w in words:
#                 if (
#                     is_subheader_title(w)
#                     and float(w.get("size", 0)) >= avg_font_size * 1.05  # 5% lebih besar dari rata-rata
#                 ):
#                     final_subheaders.append(w["text"].strip())

#     return list(dict.fromkeys(final_subheaders))  # hapus duplikat, urutan tetap

def extract_abstract(pdf_path):
    brs_title = extract_brs_title(pdf_path)
    with pdfplumber.open(pdf_path) as pdf:
        if len(pdf.pages) < 2:
            return "Abstrak tidak ditemukan"

        page = pdf.pages[1]

        # Ambil words dengan informasi font size
        words = page.extract_words(extra_attrs=["size"])

        # Gabungkan words menjadi baris berdasarkan y0 (posisi vertical)
        lines_map = {}
        for w in words:
            line_y = round(w["top"], 1)
            if line_y not in lines_map:
                lines_map[line_y] = {"text": [], "sizes": []}
            lines_map[line_y]["text"].append(w["text"])
            lines_map[line_y]["sizes"].append(w["size"])

        extracted_lines = []

        # Tentukan ukuran font normal (isi paragraf)
        # ambil median sebagai baseline
        all_sizes = [size for l in lines_map.values() for size in l["sizes"]]
        baseline_size = sorted(all_sizes)[len(all_sizes)//2]

        for line in sorted(lines_map.keys()):
            text = " ".join(lines_map[line]["text"]).strip()
            avg_size = sum(lines_map[line]["sizes"]) / len(lines_map[line]["sizes"])

            # ❌ Skip nomor halaman
            if re.fullmatch(r"\d+", text):
                continue

            # ❌ Skip footer (BRS No..., tanggal, dsb.)
            if "BRS No" in text:
                continue
            if re.search(r"\d{1,2}\s+(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s+\d{4}", text):
                # tapi jangan skip kalau font size normal (isi paragraf)
                if avg_size > baseline_size + 1:
                    continue
            if "Provinsi" in text and re.search(r"\d{4}", text):
                if avg_size > baseline_size + 1:
                    continue

            if brs_title.lower() in text.lower():
                continue


            # ❌ Skip subjudul → font lebih besar
            if avg_size > baseline_size + 1.5:
                continue

            extracted_lines.append(text)

        cleaned = " ".join(extracted_lines)
        cleaned = " ".join(cleaned.split())

        return cleaned if cleaned else "Abstrak tidak ditemukan"

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
    
# def extract_description_from_pdf(pdf_path, table_names):
#     """
#     Ekstrak deskripsi dari PDF untuk metadata setiap tabel.
#     Mengambil deskripsi sebelum nama tabel yang ada di 'table_names'.
#     Jika tabel memiliki nama dengan "(lanjutan)", gunakan deskripsi yang sama dengan tabel sebelumnya.
#     """
#     with pdfplumber.open(pdf_path) as pdf:
#         full_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
#         descriptions = {}
        
#         # Temukan semua kemunculan nama tabel dalam teks dan ambil deskripsi sebelum kata tersebut
#         for table_name in table_names:
#             # Periksa apakah tabel ini adalah "lanjutan"
#             is_continuation = "(Lanjutan)" in table_name
            
#             # Jika tabel ini adalah lanjutan, kita akan mencari deskripsi dari tabel utama
#             base_table_name = table_name.replace(" (Lanjutan)", "") if is_continuation else table_name
            
#             # Jika deskripsi untuk tabel utama sudah ada, gunakan deskripsi yang sama
#             if base_table_name in descriptions:
#                 continue  # Skip jika deskripsi untuk tabel utama sudah ada
            
#             # Cari posisi nama tabel di dalam teks
#             table_matches = re.finditer(r'(.*?)(%s)' % re.escape(table_name), full_text, re.DOTALL)

#             for match in table_matches:
#                 # Ambil teks sebelum nama tabel ditemukan
#                 text_before_table = match.group(1).strip()

#                 # # Mengambil kalimat yang diakhiri dengan titik
#                 # sentences = re.findall(r'([^.]*\.)', text_before_table)  # Kalimat yang diakhiri titik
#                 # description = ' '.join(sentences[-4:])  # Ambil 3-4 kalimat terakhir
#                 sentences = re.findall(r'[^.]*\.', text_before_table)
#                 if len(sentences) <= 4:
#                     description = ' '.join(sentences)
#                 else:
#                     description = ' '.join(sentences[-4:])


#                 # Jika deskripsi ditemukan, simpan deskripsi
#                 if description:
#                     descriptions[base_table_name] = description.strip()
                
#         # Setelah semua nama tabel diproses, kembalikan deskripsi yang sesuai
#         # Untuk setiap tabel lanjutan, gunakan deskripsi dari tabel utama
#         final_descriptions = []
#         for table_name in table_names:
#             base_table_name = table_name.replace(" (Lanjutan)", "")
#             final_descriptions.append(descriptions.get(base_table_name, "Deskripsi tidak ditemukan"))
        
#         return final_descriptions

# def extract_description_from_pdf(pdf_path, table_names):
#     """
#     Ekstrak deskripsi dari PDF untuk metadata setiap tabel.
#     Mengambil deskripsi sebelum nama tabel dan setelah nama gambar.
#     Jika tabel memiliki nama dengan "(Lanjutan)", gunakan deskripsi yang sama dengan tabel sebelumnya.
#     """
#     with pdfplumber.open(pdf_path) as pdf:
#         full_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
#         descriptions = {}

#         # Ambil semua judul gambar
#         image_titles = extract_image_titles(full_text)
#         subheader_titles = extract_subheader_titles(pdf_path)

#         for table_name in table_names:
#             is_continuation = "(Lanjutan)" in table_name
#             base_table_name = table_name.replace(" (Lanjutan)", "") if is_continuation else table_name

#             if base_table_name in descriptions:
#                 continue  # deskripsi sudah ada, skip

#             # cari posisi tabel
#             table_pos = full_text.find(table_name)
#             if table_pos == -1:
#                 print(f"⚠️ Header tabel '{table_name}' tidak ditemukan di teks.")
#                 continue

#             # cari posisi gambar terakhir sebelum tabel
#             last_image_pos = -1
#             last_image_title = None
#             for img_title in image_titles:
#                 pos = full_text.find(img_title)
#                 if pos != -1 and pos < table_pos:
#                     last_image_pos = pos
#                     last_image_title = img_title

#             # cari posisi subheader terakhir sebelum tabel
#             last_subheader_pos = -1
#             last_subheader = None
#             for sub_title in subheader_titles:
#                 pos = full_text.find(sub_title)
#                 if pos != -1 and pos < table_pos:
#                     last_subheader_pos = pos
#                     last_subheader = sub_title

#             # ambil teks antara subheader/gambar terakhir dan tabel
#             start_pos = max(last_image_pos, last_subheader_pos)
#             if start_pos != -1:
#                 segment = full_text[start_pos + len(last_subheader or last_image_title):table_pos].strip()
#             else:
#                 segment = full_text[:table_pos].strip()

#             # # ambil deskripsi: teks antara gambar terakhir dan tabel
#             # if last_image_pos != -1:
#             #     segment = full_text[last_image_pos + len(last_image_title):table_pos].strip()
#             # else:
#             #     # kalau tidak ada gambar sebelumnya, ambil beberapa kalimat sebelum tabel
#             #     segment = full_text[:table_pos].strip()

#             # ekstrak kalimat yang diakhiri titik
#             sentences = re.findall(r'[^.]*\.', segment)
#             if len(sentences) <= 4:
#                 description = ' '.join(sentences)
#             else:
#                 description = ' '.join(sentences[-4:])

#             # if description:
#             #     descriptions[base_table_name] = description.strip()
#             #     print(f"✅ Ditemukan deskripsi untuk '{table_name}'")
#             # else:

#             #     print(f"⚠️ Tidak ditemukan deskripsi untuk '{table_name}'")
#             if description:
#                 descriptions[base_table_name] = description.strip()
#                 print(f"✅ Ditemukan deskripsi untuk '{table_name}' (subheader: {last_subheader or '-'})")
#             else:
#                 print(f"⚠️ Tidak ditemukan deskripsi untuk '{table_name}'")

#         # hasil akhir: pastikan lanjutan pakai deskripsi tabel utama
#         final_descriptions = []
#         for table_name in table_names:
#             base_table_name = table_name.replace(" (Lanjutan)", "")
#             final_descriptions.append(descriptions.get(base_table_name, "Deskripsi tidak ditemukan"))

#         return final_descriptions

# import re
# import pdfplumber

# def extract_description_from_pdf(pdf_path, table_names):
#     """
#     Ekstrak deskripsi dari PDF untuk metadata setiap tabel.
#     Mengambil deskripsi sebelum nama tabel dan setelah nama gambar atau subheader.
#     Jika tabel memiliki nama dengan "(Lanjutan)", gunakan deskripsi yang sama dengan tabel sebelumnya.
#     """
#     with pdfplumber.open(pdf_path) as pdf:
#         full_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
#         descriptions = {}

#         # Ambil semua judul gambar dan subheader
#         table_titles = extract_table_names(full_text)
#         image_titles = extract_image_titles(full_text)
#         subheader_titles = extract_subheader_titles(pdf_path)

#         print("\n================ DEBUG INFO =================")
#         print(f"📄 File PDF: {pdf_path}")
#         print(f"📊 Jumlah tabel ditemukan: {len(table_names)}")
#         print(f"🖼️ Jumlah gambar ditemukan: {len(image_titles)}")
#         print(f"📚 Jumlah subheader ditemukan: {len(subheader_titles)}")

#         print("\n🖼️ Daftar Judul table titles:")
#         for img in table_titles:
#             print(f"   - {img}")

#         print("\n🖼️ Daftar Judul Tabel names:")
#         for img in table_names:
#             print(f"   - {img}")
        
#         print("\n🖼️ Daftar Judul Gambar:")
#         for img in image_titles:
#             print(f"   - {img}")

#         print("\n📚 Daftar Subheader:")
#         for sh in subheader_titles:
#             print(f"   - {sh}")
#         print("=============================================\n")

#         # Proses setiap tabel
#         for table_name in table_names:
#             is_continuation = "(Lanjutan)" in table_name
#             base_table_name = table_name.replace(" (Lanjutan)", "") if is_continuation else table_name

#             if base_table_name in descriptions:
#                 continue  # deskripsi sudah ada, skip

#             # cari posisi tabel
#             table_pos = full_text.find(table_name)
#             if table_pos == -1:
#                 print(f"⚠️ Header tabel '{table_name}' tidak ditemukan di teks.")
#                 continue

#             print(f"\n🔎 Memproses '{table_name}' ...")
#             print(f"   ➜ Posisi teks tabel: {table_pos}")

#             # cari posisi gambar terakhir sebelum tabel
#             last_image_pos = -1
#             last_image_title = None
#             for img_title in image_titles:
#                 pos = full_text.find(img_title)
#                 if pos != -1 and pos < table_pos:
#                     last_image_pos = pos
#                     last_image_title = img_title
#             if last_image_pos != -1:
#                 print(f"   🖼️ Gambar terakhir sebelum tabel: '{last_image_title}' (pos: {last_image_pos})")
#             else:
#                 print(f"   ⚠️ Tidak ada gambar sebelum tabel")

#             # cari posisi subheader terakhir sebelum tabel
#             last_subheader_pos = -1
#             last_subheader = None
#             for sub_title in subheader_titles:
#                 pos = full_text.find(sub_title)
#                 if pos != -1 and pos < table_pos:
#                     last_subheader_pos = pos
#                     last_subheader = sub_title
#             if last_subheader_pos != -1:
#                 print(f"   📚 Subheader terakhir sebelum tabel: '{last_subheader}' (pos: {last_subheader_pos})")
#             else:
#                 print(f"   ⚠️ Tidak ada subheader sebelum tabel")

#             # ambil teks antara subheader/gambar terakhir dan tabel
#             start_pos = max(last_image_pos, last_subheader_pos)
#             if start_pos != -1:
#                 segment = full_text[start_pos + len(last_subheader or last_image_title):table_pos].strip()
#             else:
#                 segment = full_text[:table_pos].strip()

#             # ekstrak kalimat yang diakhiri titik
#             sentences = re.findall(r'[^.]*\.', segment)
#             if len(sentences) <= 4:
#                 description = ' '.join(sentences)
#             else:
#                 description = ' '.join(sentences[-4:])

#             if description:
#                 descriptions[base_table_name] = description.strip()
#                 print(f"✅ Ditemukan deskripsi untuk '{table_name}' (subheader: {last_subheader or '-'})")
#                 print(f"   📝 Cuplikan Deskripsi: {description[:200]}...")
#             else:
#                 print(f"⚠️ Tidak ditemukan deskripsi untuk '{table_name}'")

#         # hasil akhir: pastikan lanjutan pakai deskripsi tabel utama
#         final_descriptions = []
#         for table_name in table_names:
#             base_table_name = table_name.replace(" (Lanjutan)", "")
#             final_descriptions.append(descriptions.get(base_table_name, "Deskripsi tidak ditemukan"))

#         print("\n================ RINGKASAN AKHIR =================")
#         for tbl, desc in zip(table_names, final_descriptions):
#             print(f"📘 {tbl} → {desc[:150]}...")
#         print("==================================================\n")

#         return final_descriptions

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

