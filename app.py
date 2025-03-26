from flask import Flask, render_template, request, send_file, redirect, url_for, jsonify, make_response, flash, session, send_from_directory
import os
import shutil
import uuid
from zipfile import ZipFile
from werkzeug.utils import secure_filename
from datetime import datetime
import io
import re
import json
import base64
import requests
from dotenv import load_dotenv
import difflib
import google.generativeai as genai
import secrets
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import tempfile
from database import init_db, db_connection

try:
    from PIL import Image
except ImportError:
    print("WARNING: PIL/Pillow not installed. Image processing will be limited.")
    Image = None

load_dotenv()

# Inisialisasi Google Drive untuk gambar
def init_drive_client():
    credentials_json = os.getenv('GOOGLE_CREDENTIALS')
    credentials_dict = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(
        credentials_dict,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=credentials)

drive_client = init_drive_client()
folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')

def find_or_create_folder(filename):
    query = f"'{folder_id}' in parents and name = '{filename}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    response = drive_client.files().list(q=query, spaces='drive', fields='files(id)').execute()
    folders = response.get('files', [])
    if folders:
        return folders[0]['id']
    folder_metadata = {
        'name': filename,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [folder_id]
    }
    folder = drive_client.files().create(body=folder_metadata, fields='id').execute()
    return folder['id']

def find_file_in_folder(filename, parent_folder_id):
    query = f"'{parent_folder_id}' in parents and name = '{filename}' and trashed = false"
    response = drive_client.files().list(q=query, spaces='drive', fields='files(id)').execute()
    files = response.get('files', [])
    return files[0]['id'] if files else None

# Gemini API key
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_AVAILABLE = True

if GEMINI_API_KEY and GEMINI_AVAILABLE:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        print("Gemini API configured successfully.")
    except Exception as e:
        print(f"Failed to configure Gemini API: {e}")
        GEMINI_AVAILABLE = False
else:
    print("Gemini API key not found or Gemini not available.")
    GEMINI_AVAILABLE = False

if GEMINI_AVAILABLE:
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        print("Gemini model 'gemini-2.0-flash' initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize Gemini model: {e}")
        GEMINI_AVAILABLE = False
else:
    model = None

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Inisialisasi database Supabase (PostgreSQL)
init_db()

# Mapping matkul ke dosen
MATKUL_DOSEN = {
    "Praktikum Struktur Data": "Dr. Umar Taufiq, S.Kom., M.Cs.",
    "Praktikum Basis Data": "Dinar Nugroho Pratomo, S.Kom., M.IM., M.Cs.",
    "Praktikum Pemrograman Web 1": "Dinar Nugroho Pratomo, S.Kom., M.IM., M.Cs."
}

# Template LaTeX
LATEX_TEMPLATE = r"""\documentclass[a4paper,oneside,12pt]{book}
% Package yang diperlukan
\usepackage{graphicx} \usepackage{titling} \usepackage{geometry} \usepackage{listings}
\usepackage{xcolor} \usepackage{float} \usepackage{hyperref} \usepackage{indentfirst}
\usepackage{url} \usepackage{fancyhdr} \newcommand{\customfbox}[2]{%
  \setlength{\fboxsep}{0pt}%
  \setlength{\fboxrule}{0.5pt}
  \fcolorbox{black}{white}{#2}
}

% Pengaturan margin umum untuk isi laporan
\geometry{left=3cm, right=2.5cm, top=2cm, bottom=2.5cm}

% Pengaturan untuk kode
\definecolor{codegreen}{rgb}{0,0.6,0}
\definecolor{codegray}{rgb}{0.5,0.5,0.5}
\definecolor{codepurple}{rgb}{0.58,0,0.82}
\definecolor{backcolour}{rgb}{0.95,0.95,0.92}
\definecolor{darkblue}{rgb}{0,0,0.6}

% Common style untuk semua listing
\lstdefinestyle{commonstyle}{
    backgroundcolor=\color{backcolour}, 
    breakatwhitespace=false, 
    breaklines=true, 
    captionpos=b, 
    keepspaces=true,
    numbers=left, 
    numbersep=5pt, 
    showspaces=false, 
    showstringspaces=false,
    showtabs=false, 
    tabsize=2, 
    frame=single,
    basicstyle=\ttfamily\footnotesize,
    numberstyle=\tiny\color{codegray}
}

% Pengaturan untuk kode HTML
\lstdefinestyle{htmlstyle}{
    style=commonstyle,
    language=HTML,
    commentstyle=\color{codegreen},
    keywordstyle=\color{codepurple},
    stringstyle=\color{codegreen}
}

% Pengaturan untuk kode Python
\lstdefinestyle{pythonstyle}{
    style=commonstyle,
    language=Python,
    commentstyle=\color{codegreen},
    keywordstyle=\color{darkblue},
    stringstyle=\color{codepurple},
    emph={import,from,class,def,for,while,if,else,elif,try,except,finally},
    emphstyle=\color{darkblue}
}

% Pengaturan untuk kode SQL
\lstdefinestyle{sqlstyle}{
    style=commonstyle,
    language=SQL,
    commentstyle=\color{codegreen},
    keywordstyle=\color{darkblue},
    stringstyle=\color{codepurple},
    emph={SELECT,FROM,WHERE,INSERT,UPDATE,DELETE,CREATE,DROP},
    emphstyle=\color{darkblue}
}

% Pengaturan untuk kode JavaScript
\lstdefinestyle{javascriptstyle}{
    style=commonstyle,
    language=JavaScript,
    commentstyle=\color{codegreen},
    keywordstyle=\color{darkblue},
    stringstyle=\color{codepurple},
    emph={function,var,let,const,return,if,for,while,do,else,switch,case},
    emphstyle=\color{darkblue}
}

\lstdefinestyle{cssstyle}{
    style=commonstyle,
    language=CSS,
    commentstyle=\color{codegreen},
    keywordstyle=\color{darkblue},
    stringstyle=\color{codepurple},
    emph={color, background, font, margin, padding, border, display, position, width, height},
    emphstyle=\color{darkblue}
}

% Pengaturan untuk URL
\hypersetup{
    colorlinks=true, 
    linkcolor=black, 
    filecolor=black, 
    urlcolor=black,
    pdftitle={Laporan Praktikum}, 
    pdfpagemode=FullScreen, 
    breaklinks=true
}

% Pengaturan untuk nomor halaman di tengah bawah
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0pt}

\fancypagestyle{plain}{
    \fancyhf{}
    \fancyfoot[C]{\thepage}
    \renewcommand{\headrulewidth}{0pt}
}

% Judul, Penulis, Tanggal
\title{Laporan Praktikum \\ MATKUL \\ Pertemuan PERTEMUAN \\ JUDUL}
\date{TANGGAL}

% Penyesuaian nama Daftar Pustaka dan Daftar Isi
\renewcommand\bibname{Daftar Pustaka}
\renewcommand{\contentsname}{Daftar Isi}

\begin{document}

% Halaman Cover dengan margin khusus
\newgeometry{left=3cm, right=2.5cm, top=3cm, bottom=3cm}
\begin{titlingpage}
\begin{center}
\vspace{4cm}
\begin{huge}
\textbf{\thetitle} \\
\end{huge}
\vspace{1cm}
\includegraphics[height=9.5cm]{lambang ugm.png} \\
\vspace{1cm}
\begin{Large}
\textbf{Disusun oleh:} \\
\vspace{0.5cm}
NAMA \\
NPM \\
KELAS \\
\end{Large}
\vspace{1cm}
\begin{Large}
\textbf{Dosen Pengampu:} \\
\vspace{0.5cm}
DOSEN \\
\end{Large}
\vspace{1cm}
\thedate
\end{center}
\end{titlingpage}
\restoregeometry

% Daftar Isi
\tableofcontents
\newpage

\chapter*{Tujuan Praktikum}
\addcontentsline{toc}{chapter}{Tujuan Praktikum}
\begin{enumerate}
TUJUAN
\end{enumerate}

\chapter*{Dasar Teori}
\addcontentsline{toc}{chapter}{Dasar Teori}
\setcounter{chapter}{2}
\setcounter{section}{0}
DASAR_TEORI

\chapter*{Hasil dan Pembahasan}
\addcontentsline{toc}{chapter}{Hasil dan Pembahasan}
\setcounter{chapter}{3}
\setcounter{section}{0}
HASIL_PEMBAHASAN

\chapter*{Kesimpulan}
\addcontentsline{toc}{chapter}{Kesimpulan}
\setcounter{chapter}{4}
\setcounter{section}{0}
KESIMPULAN

\newpage
\addcontentsline{toc}{chapter}{Daftar Pustaka}
\begin{thebibliography}{99}
REFERENSI
\end{thebibliography}

\end{document}
"""

# Fungsi utilitas
def get_filenames():
    """Mendapatkan daftar filename dari Supabase (PostgreSQL)"""
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT filename, metadata FROM laporan')
            laporans = cursor.fetchall()
            filenames = []
            for laporan in laporans:
                metadata = json.loads(laporan['metadata']) if laporan['metadata'] else {}
                filenames.append({
                    'filename': laporan['filename'],
                    'nama': metadata.get('nama', ''),
                    'judul': metadata.get('judul', ''),
                    'matkul': metadata.get('matkul', ''),
                    'tanggal': metadata.get('tanggal', ''),
                    'last_modified': metadata.get('tanggal', '')  # Gunakan tanggal sebagai proxy
                })

        filenames.sort(key=lambda x: x['last_modified'], reverse=True)
        return filenames
    except Exception as e:
        print(f"❌ Error getting filenames from Supabase: {e}")
        return []

def standardize_filename(name, npm, matkul, judul):
    """Membuat nama file yang konsisten"""
    base = f"{name}_{npm}_{matkul}_{judul}"
    sanitized = re.sub(r'[\/\\:*?"<>|]', '_', base).replace(' ', '_')
    return sanitized

def process_tujuan(tujuan_text):
    """Proses tujuan ke format LaTeX itemize"""
    if not tujuan_text:
        return r'\item Memenuhi tugas praktikum'
    lines = tujuan_text.strip().split('\n')
    items = [f'\\item {line.strip()}' for line in lines if line.strip()]
    return '\n'.join(items) if items else r'\item Memenuhi tugas praktikum'

def process_referensi(referensi_text):
    """Proses referensi ke format LaTeX bibliography tanpa \bibitem"""
    if not referensi_text or not referensi_text.strip():
        return '-'  # Default jika kosong
    lines = referensi_text.strip().split('\n')
    items = [line.strip() for line in lines if line.strip()]
    return '\n'.join(items) if items else '-'

def generate_latex_for_dasar_teori(sections):
    """Generate LaTeX untuk dasar teori"""
    if not sections:
        return ""
        
    print(f"Generating LaTeX for {len(sections)} dasar teori sections")
    content = ""
    
    for section_id, section in sorted(sections.items(), key=lambda x: int(x[0]) if x[0].isdigit() else float('inf')):
        title = section.get('title', '')
        print(f"Processing dasar teori section {section_id}: {title}")
        
        raw_content = section.get('content', '')
        image = section.get('image', '')
        
        if raw_content:
            print(f"Section {section_id} content: {len(raw_content)} chars, {raw_content.count('\\')} backslashes")
        else:
            print(f"Section {section_id} has no content!")
        
        if title:
            content += f"\\section{{{title}}}\n"
        
        if raw_content:
            content += raw_content + "\n\n"
            
            if "begin{" in raw_content and "\\begin{" not in raw_content:
                print(f"WARNING: LaTeX tags missing backslashes in section {section_id}")
                
        if image:
            filename_img = os.path.basename(image)
            content += f"\\begin{{figure}}[H]\n" \
                       f"\\centering\n" \
                       f"\\customfbox{{1pt}}{{\n" \
                       f"    \\includegraphics[width=0.78\\textwidth, keepaspectratio]{{{filename_img}}}\n" \
                       f"}}\n" \
                       f"\\caption{{{title}}}\n" \
                       f"\\label{{fig:{section_id}}}\n" \
                       f"\\end{{figure}}\n\n"
            print(f"Added image {filename_img} for section {section_id}")
            
    return content

def generate_latex_for_sections(sections):
    """Generate LaTeX untuk hasil dan pembahasan"""
    if not sections:
        return ""
        
    print(f"Generating LaTeX for {len(sections)} sections")
    latex = ""
    section_groups = {}
    
    for id, data in sections.items():
        if data.get('type') == 'section':
            section_groups[id] = {'title': data['title'], 'subsections': []}
            print(f"Found main section {id}: {data['title']}")
            
    for id, data in sections.items():
        if data.get('type') == 'subsection':
            parent_id = data.get('parent_section', next(iter(section_groups)) if section_groups else 'default')
            if parent_id not in section_groups:
                section_groups[parent_id] = {'title': 'Latihan', 'subsections': []}
                print(f"Created default parent section for subsection {id}")
                
            section_groups[parent_id]['subsections'].append({
                'id': id,
                'title': data['title'], 
                'code': data.get('code', ''),
                'image': data.get('image', ''),
                'penjelasan': data.get('penjelasan', '')
            })
            print(f"Added subsection {id} to parent {parent_id}")
    
    for section_id, section_data in section_groups.items():
        if not section_data['subsections']:
            print(f"Section {section_id} has no subsections, skipping")
            continue
            
        latex += f"\\section{{{section_data['title']}}}\n\n"
        print(f"Adding section {section_id} with {len(section_data['subsections'])} subsections")
        
        for subsection in section_data['subsections']:
            latex += f"\\subsection{{{subsection['title']}}}\n\n"
            
            if subsection['code']:
                latex += f"\\begin{{lstlisting}}[language=Python, style=pythonstyle]\n{subsection['code']}\n\\end{{lstlisting}}\n\n"
                print(f"Added code for subsection {subsection['id']}")
                
            if subsection['image']:
                img_filename = os.path.basename(subsection['image'])
                latex += f"\\begin{{figure}}[H]\n" \
                        f"\\centering\n" \
                        f"\\customfbox{{1pt}}{{\n" \
                        f"    \\includegraphics[width=0.78\\textwidth, keepaspectratio]{{{img_filename}}}\n" \
                        f"}}\n" \
                        f"\\caption{{{subsection['title']}}}\n" \
                        f"\\label{{fig:{subsection['id']}}}\n" \
                        f"\\end{{figure}}\n\n"
                print(f"Added image {img_filename} for subsection {subsection['id']}")
                
            if subsection['penjelasan']:
                latex += f"\\textbf{{Penjelasan:}} {subsection['penjelasan']}\n\n"
                print(f"Added explanation for subsection {subsection['id']}")
                
    if not latex:
        print("WARNING: No content generated for LaTeX sections")
        latex = "\\section{Hasil dan Pembahasan}\nTidak ada data hasil dan pembahasan.\n\n"
        
    return latex

# Routes
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        nama = request.form.get('nama', '').strip()
        npm = request.form.get('npm', '').strip()
        matkul = request.form.get('matkul', '').strip()
        pertemuan = request.form.get('pertemuan', '').strip()
        judul = request.form.get('judul', '').strip()
        tanggal = request.form.get('tanggal', '').strip()
        kelas = request.form.get('kelas', '').strip()
        dosen = request.form.get('dosen', '').strip()
        tujuan = request.form.get('tujuan', '').strip()
        kesimpulan = request.form.get('kesimpulan', '').strip()
        referensi = request.form.get('referensi', '').strip()
        action = request.form.get('action', 'save')
        edit_mode = request.form.get('edit_mode') == 'true'
        original_filename = request.form.get('original_filename', '')

        def clean_text(text):
            if not text:
                return ''
            text = text.strip()
            text = re.sub(r'\n\s*\n+', '\n', text)
            return text

        tujuan = clean_text(tujuan)
        kesimpulan = clean_text(kesimpulan)
        referensi = clean_text(referensi)

        if not all([nama, npm, matkul, judul]):
            flash('Nama, NPM, Mata Kuliah, dan Judul harus diisi!', 'error')
            return render_template('form.html', form_data=request.form, matkul_dosen=MATKUL_DOSEN, filenames=get_filenames())

        filename = standardize_filename(nama, npm, matkul, judul)

        # Process Dasar Teori Sections
        dasar_teori_sections = {}
        for key in request.form:
            if key.startswith('dasar_teori_section_id_'):
                section_id = request.form[key]
                content_key = f'dasar_teori_section_content_{section_id}'
                raw_content = request.form.get(content_key, '').strip()
                raw_content = clean_text(raw_content)
                dasar_teori_sections[section_id] = {
                    'title': request.form.get(f'dasar_teori_section_title_{section_id}', '').strip(),
                    'content': raw_content,
                    'image': request.form.get(f'dasar_teori_section_image_{section_id}', '').strip()
                }

        # Process Main Sections
        main_sections = {}
        for key in request.form:
            if key.startswith('section_type_'):
                section_id = key[len('section_type_'):]
                section_type = request.form[key]
                main_sections[section_id] = {
                    'type': section_type,
                    'title': request.form.get(f'section_title_{section_id}', '').strip()
                }
                if section_type == 'subsection':
                    parent_key = f'parent_section_{section_id}'
                    code_key = f'code_{section_id}'
                    penjelasan_key = f'penjelasan_{section_id}'
                    code_content = request.form.get(code_key, '').strip()
                    penjelasan_content = request.form.get(penjelasan_key, '').strip()
                    code_content = clean_text(code_content)
                    penjelasan_content = clean_text(penjelasan_content)
                    if parent_key in request.form:
                        main_sections[section_id]['parent_section'] = request.form[parent_key]
                    if code_key in request.form:
                        main_sections[section_id]['code'] = code_content
                    if penjelasan_key in request.form:
                        main_sections[section_id]['penjelasan'] = penjelasan_content
                    main_sections[section_id]['image'] = request.form.get(f'image_{section_id}', '').strip()

        # Simpan metadata
        metadata = {
            'filename': filename,
            'matkul': matkul,
            'pertemuan': pertemuan,
            'judul': judul,
            'tanggal': tanggal,
            'nama': nama,
            'npm': npm,
            'kelas': kelas,
            'dosen': dosen,
            'tujuan': tujuan,
            'kesimpulan': kesimpulan,
            'referensi': referensi,
            'dasar_teori_sections': dasar_teori_sections,
            'main_sections': main_sections
        }

        # Simpan ke Supabase (PostgreSQL)
        try:
            with db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO laporan (filename, metadata, tujuan, kesimpulan, referensi)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (filename) DO UPDATE
                    SET metadata = EXCLUDED.metadata,
                        tujuan = EXCLUDED.tujuan,
                        kesimpulan = EXCLUDED.kesimpulan,
                        referensi = EXCLUDED.referensi
                ''', (filename, json.dumps(metadata), tujuan, kesimpulan, referensi))

                cursor.execute('DELETE FROM sections WHERE filename = %s', (filename,))

                for section_id, section in dasar_teori_sections.items():
                    cursor.execute('''
                        INSERT INTO sections (filename, section_id, type, title, content, image)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (filename, f"dasar_teori_{section_id}", 'dasar_teori', section['title'], section['content'], section['image']))

                for section_id, section in main_sections.items():
                    if section['type'] == 'section':
                        cursor.execute('''
                            INSERT INTO sections (filename, section_id, type, title)
                            VALUES (%s, %s, %s, %s)
                        ''', (filename, section_id, 'section', section['title']))
                    else:
                        cursor.execute('''
                            INSERT INTO sections (filename, section_id, type, title, content, image, parent_section)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ''', (filename, section_id, 'subsection', section['title'], section.get('code', ''), section.get('image', ''), section.get('parent_section', '')))
                        cursor.execute('''
                            INSERT INTO sections (filename, section_id, type, title, content, parent_section)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        ''', (filename, f"penjelasan_{section_id}", 'penjelasan', section['title'], section.get('penjelasan', ''), section_id))

                conn.commit()
        except Exception as e:
            print(f"❌ Error saving to Supabase: {e}")
            flash(f'Error saving data to database: {str(e)}', 'error')
            return render_template('form.html', form_data=request.form, matkul_dosen=MATKUL_DOSEN, filenames=get_filenames())

        # Jika edit mode, salin file gambar dari folder lama di Google Drive
        if edit_mode and original_filename and original_filename != filename:
            try:
                old_folder_id = find_or_create_folder(original_filename)
                new_folder_id = find_or_create_folder(filename)

                query = f"'{old_folder_id}' in parents and trashed = false"
                response = drive_client.files().list(
                    q=query,
                    spaces='drive',
                    fields='files(id, name, mimeType)'
                ).execute()
                files = response.get('files', [])

                for file in files:
                    if file['mimeType'].startswith('image/') or 'lambang' in file['name'].lower():
                        file_metadata = {
                            'name': file['name'],
                            'parents': [new_folder_id]
                        }
                        drive_client.files().copy(
                            fileId=file['id'],
                            body=file_metadata
                        ).execute()
                        print(f"Copied {file['name']} from {original_filename} to {filename}")
            except Exception as e:
                print(f"❌ Error copying files from {original_filename} to {filename}: {e}")

        session['last_filename'] = filename
        flash('Data tersimpan sukses!', 'success')
        return redirect(url_for('edit', filename=filename) if action == 'save' else url_for('generate_latex', filename=filename))

    last_filename = session.get('last_filename')
    if last_filename:
        try:
            with db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM laporan WHERE filename = %s', (last_filename,))
                laporan = cursor.fetchone()
                if not laporan:
                    return render_template('form.html', form_data=None, matkul_dosen=MATKUL_DOSEN, filenames=get_filenames())

                metadata = json.loads(laporan['metadata']) if laporan['metadata'] else {}
                cursor.execute('SELECT * FROM sections WHERE filename = %s', (last_filename,))
                sections = cursor.fetchall()
                dasar_teori_sections = {}
                main_sections = {}

                for section in sections:
                    if section['type'] == 'dasar_teori':
                        section_id = section['section_id'].replace('dasar_teori_', '')
                        dasar_teori_sections[section_id] = {
                            'title': section['title'],
                            'content': section['content'],
                            'image': section['image']
                        }
                    elif section['type'] == 'section':
                        main_sections[section['section_id']] = {
                            'type': 'section',
                            'title': section['title']
                        }
                    elif section['type'] == 'subsection':
                        main_sections[section['section_id']] = {
                            'type': 'subsection',
                            'title': section['title'],
                            'code': section['content'],
                            'image': section['image'],
                            'parent_section': section['parent_section']
                        }
                    elif section['type'] == 'penjelasan':
                        section_id = section['parent_section']
                        if section_id in main_sections:
                            main_sections[section_id]['penjelasan'] = section['content']

                metadata['dasar_teori_sections'] = dasar_teori_sections
                metadata['main_sections'] = main_sections
                metadata['tujuan'] = laporan['tujuan']
                metadata['kesimpulan'] = laporan['kesimpulan']
                metadata['referensi'] = laporan['referensi']
        except Exception as e:
            print(f"❌ Error loading last filename from Supabase: {e}")
            flash(f'Error loading last file: {str(e)}', 'error')
            return render_template('form.html', form_data=None, matkul_dosen=MATKUL_DOSEN, filenames=get_filenames())

        flash(f'Melanjutkan pengeditan {last_filename}', 'info')
        return render_template('form.html', form_data=metadata, matkul_dosen=MATKUL_DOSEN, filenames=get_filenames())
    return render_template('form.html', form_data=None, matkul_dosen=MATKUL_DOSEN, filenames=get_filenames())

@app.route('/edit/<filename>')
def edit(filename):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM laporan WHERE filename = %s', (filename,))
            laporan = cursor.fetchone()
            if not laporan:
                flash(f'File {filename} tidak ditemukan', 'error')
                return redirect('/')

            metadata = json.loads(laporan['metadata']) if laporan['metadata'] else {}
            cursor.execute('SELECT * FROM sections WHERE filename = %s', (filename,))
            sections = cursor.fetchall()
            dasar_teori_sections = {}
            main_sections = {}

            for section in sections:
                if section['type'] == 'dasar_teori':
                    section_id = section['section_id'].replace('dasar_teori_', '')
                    dasar_teori_sections[section_id] = {
                        'title': section['title'],
                        'content': section['content'],
                        'image': section['image']
                    }
                elif section['type'] == 'section':
                    main_sections[section['section_id']] = {
                        'type': 'section',
                        'title': section['title']
                    }
                elif section['type'] == 'subsection':
                    main_sections[section['section_id']] = {
                        'type': 'subsection',
                        'title': section['title'],
                        'code': section['content'],
                        'image': section['image'],
                        'parent_section': section['parent_section']
                    }
                elif section['type'] == 'penjelasan':
                    section_id = section['parent_section']
                    if section_id in main_sections:
                        main_sections[section_id]['penjelasan'] = section['content']

            metadata['dasar_teori_sections'] = dasar_teori_sections
            metadata['main_sections'] = main_sections
            metadata['tujuan'] = laporan['tujuan']
            metadata['kesimpulan'] = laporan['kesimpulan']
            metadata['referensi'] = laporan['referensi']

        print(f"Loading edit form for {filename}")
        print(f"Metadata keys: {list(metadata.keys())}")

        session['last_filename'] = filename
        
        print("Verification before sending to template:")
        print(f"- Dasar teori sections: {len(metadata.get('dasar_teori_sections', {}))}")
        for section_id, section in metadata.get('dasar_teori_sections', {}).items():
            print(f"  - Section {section_id}: {section.get('title')}, content: {len(section.get('content', ''))} chars")
            
        print(f"- Main sections: {len(metadata.get('main_sections', {}))}")
        for section_id, section in metadata.get('main_sections', {}).items():
            if section.get('type') == 'section':
                print(f"  - Section {section_id}: {section.get('title')}")
            elif section.get('type') == 'subsection':
                print(f"  - Subsection {section_id}: {section.get('title')}, code: {len(section.get('code', ''))} chars, penjelasan: {len(section.get('penjelasan', ''))} chars")
        
        return render_template('form.html', form_data=metadata, matkul_dosen=MATKUL_DOSEN, filenames=get_filenames())
        
    except Exception as e:
        import traceback
        print(f"ERROR in edit route: {str(e)}")
        traceback.print_exc()
        flash(f'Error loading file {filename}: {str(e)}', 'error')
        return redirect('/')

@app.route('/generate_latex/<filename>')
def generate_latex(filename):
    print(f"Generating LaTeX for {filename}")
    
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM laporan WHERE filename = %s', (filename,))
            laporan = cursor.fetchone()
            if not laporan:
                flash(f'File {filename} tidak ditemukan', 'error')
                return redirect('/')

            metadata = json.loads(laporan['metadata']) if laporan['metadata'] else {}
            cursor.execute('SELECT * FROM sections WHERE filename = %s', (filename,))
            sections = cursor.fetchall()
            dasar_teori_sections = {}
            main_sections = {}

            for section in sections:
                if section['type'] == 'dasar_teori':
                    section_id = section['section_id'].replace('dasar_teori_', '')
                    dasar_teori_sections[section_id] = {
                        'title': section['title'],
                        'content': section['content'],
                        'image': section['image']
                    }
                elif section['type'] == 'section':
                    main_sections[section['section_id']] = {
                        'type': 'section',
                        'title': section['title']
                    }
                elif section['type'] == 'subsection':
                    main_sections[section['section_id']] = {
                        'type': 'subsection',
                        'title': section['title'],
                        'code': section['content'],
                        'image': section['image'],
                        'parent_section': section['parent_section']
                    }
                elif section['type'] == 'penjelasan':
                    section_id = section['parent_section']
                    if section_id in main_sections:
                        main_sections[section_id]['penjelasan'] = section['content']

            metadata['dasar_teori_sections'] = dasar_teori_sections
            metadata['main_sections'] = main_sections
            metadata['tujuan'] = laporan['tujuan']
            metadata['kesimpulan'] = laporan['kesimpulan']
            metadata['referensi'] = laporan['referensi']

        project_folder_id = find_or_create_folder(filename)
        logo_file_id = find_file_in_folder('lambang ugm.png', project_folder_id)
        if not logo_file_id:
            default_logo = os.path.join(app.static_folder, 'lambang ugm.png')
            if os.path.exists(default_logo):
                file_metadata = {
                    'name': 'lambang ugm.png',
                    'parents': [project_folder_id]
                }
                media = MediaFileUpload(default_logo, mimetype='image/png')
                drive_client.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                print(f"Uploaded lambang ugm.png to Google Drive for {filename}")

        latex_content = LATEX_TEMPLATE
        
        dasar_teori_latex = generate_latex_for_dasar_teori(dasar_teori_sections)
        print(f"Generated dasar teori LaTeX: {len(dasar_teori_latex)} chars")
        
        hasil_pembahasan_latex = generate_latex_for_sections(main_sections)
        print(f"Generated hasil pembahasan LaTeX: {len(hasil_pembahasan_latex)} chars")
        
        replacements = {
            'MATKUL': metadata.get('matkul', ''),
            'PERTEMUAN': metadata.get('pertemuan', ''),
            'JUDUL': metadata.get('judul', ''),
            'TANGGAL': metadata.get('tanggal', ''),
            'NAMA': metadata.get('nama', ''),
            'NPM': metadata.get('npm', ''),
            'KELAS': metadata.get('kelas', ''),
            'DOSEN': metadata.get('dosen', ''),
            'TUJUAN': process_tujuan(metadata.get('tujuan', '')),
            'DASAR_TEORI': dasar_teori_latex,
            'HASIL_PEMBAHASAN': hasil_pembahasan_latex,
            'KESIMPULAN': metadata.get('kesimpulan', ''),
            'REFERENSI': process_referensi(metadata.get('referensi', ''))
        }
        
        for key, value in replacements.items():
            if value is None:
                value = ''
            latex_content = latex_content.replace(key, value)
            print(f"Replaced {key} with {len(value)} chars")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            tex_file = os.path.join(temp_dir, f"{filename}.tex")
            with open(tex_file, 'w', encoding='utf-8') as f:
                f.write(latex_content)
            print(f"Saved LaTeX content to {tex_file}")
            
            session['tex_file_path'] = tex_file
        
        images = []
        for section in dasar_teori_sections.values():
            if section.get('image'):
                images.append({'name': os.path.basename(section['image'])})
        for section in main_sections.values():
            if section.get('type') == 'subsection' and section.get('image'):
                images.append({'name': os.path.basename(section['image'])})
        if logo_file_id:
            images.append({'name': 'lambang ugm.png'})
        
        return render_template('output.html', 
                              filename=filename,
                              form_data=metadata, 
                              latex_content=latex_content,
                              images=images,
                              dasar_teori_length=len(dasar_teori_latex),
                              hasil_pembahasan_length=len(hasil_pembahasan_latex))
                               
    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f'Error generating LaTeX: {str(e)}', 'error')
        return redirect(url_for('edit', filename=filename))

@app.route('/download_image_zip/<filename>')
def download_image_zip(filename):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM laporan WHERE filename = %s', (filename,))
            laporan = cursor.fetchone()
            if not laporan:
                flash(f'File {filename} tidak ditemukan', 'error')
                return redirect(url_for('generate_latex', filename=filename))

            metadata = json.loads(laporan['metadata']) if laporan['metadata'] else {}
            cursor.execute('SELECT * FROM sections WHERE filename = %s', (filename,))
            sections = cursor.fetchall()
            dasar_teori_sections = {}
            main_sections = {}

            for section in sections:
                if section['type'] == 'dasar_teori':
                    section_id = section['section_id'].replace('dasar_teori_', '')
                    dasar_teori_sections[section_id] = {
                        'title': section['title'],
                        'content': section['content'],
                        'image': section['image']
                    }
                elif section['type'] == 'section':
                    main_sections[section['section_id']] = {
                        'type': 'section',
                        'title': section['title']
                    }
                elif section['type'] == 'subsection':
                    main_sections[section['section_id']] = {
                        'type': 'subsection',
                        'title': section['title'],
                        'code': section['content'],
                        'image': section['image'],
                        'parent_section': section['parent_section']
                    }

            images = []
            for section in dasar_teori_sections.values():
                if section.get('image'):
                    images.append(section['image'])
            for section in main_sections.values():
                if section.get('type') == 'subsection' and section.get('image'):
                    images.append(section['image'])
            project_folder_id = find_or_create_folder(filename)
            logo_file_id = find_file_in_folder('lambang ugm.png', project_folder_id)
            if logo_file_id:
                images.append(f"{filename}/lambang ugm.png")

        if not images:
            flash('No images found to download', 'error')
            return redirect(url_for('generate_latex', filename=filename))

        memory_file = io.BytesIO()
        with ZipFile(memory_file, 'w') as zf:
            for image_path in images:
                parts = image_path.split('/')
                if len(parts) < 2:
                    continue
                folder = '/'.join(parts[:-1])
                image_name = parts[-1]

                project_folder_id = find_or_create_folder(folder)
                file_id = find_file_in_folder(image_name, project_folder_id)
                if not file_id:
                    continue

                request = drive_client.files().get_media(fileId=file_id)
                file_stream = io.BytesIO()
                downloader = MediaIoBaseDownload(file_stream, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                file_stream.seek(0)

                zf.writestr(image_name, file_stream.read())

        memory_file.seek(0)
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{filename}_images.zip"
        )
    except Exception as e:
        print(f"❌ Error downloading images as ZIP: {e}")
        flash('Error downloading images', 'error')
        return redirect(url_for('generate_latex', filename=filename))

@app.route('/download_tex/<filename>')
def download_tex(filename):
    tex_file = session.get('tex_file_path')
    if tex_file and os.path.exists(tex_file):
        return send_file(tex_file, as_attachment=True, download_name=f"{filename}.tex")
    flash('File LaTeX tidak ditemukan', 'error')
    return redirect(url_for('edit', filename=filename))

@app.route('/convert-to-latex', methods=['POST'])
def convert_to_latex():
    if not GEMINI_AVAILABLE or model is None:
        return jsonify({'success': False, 'error': 'Gemini API is not available'}), 503

    data = request.get_json()
    text = data.get('text', '')
    preserve = data.get('preserve', True)

    if not text:
        return jsonify({'success': False, 'error': 'Text is empty'}), 400

    try:
        prompt = (f"Convert the following text to LaTeX format, but DO NOT include any LaTeX document "
                 f"preamble (no \\documentclass, \\usepackage, \\begin{{document}}, etc). "
                 f"Just provide the content LaTeX commands:\n\n{text}\n\n"
                 f"Ensure the output uses proper LaTeX syntax like \\section, \\textbf, \\item, etc. "
                 f"Do not add any document structure commands.")
        if preserve:
            prompt += "\nPreserve the original formatting as much as possible."

        response = model.generate_content(prompt)
        latex_text = response.text.strip()

        latex_text = re.sub(r'\\documentclass(\[.*?\])?\{.*?\}', '', latex_text)
        latex_text = re.sub(r'\\usepackage(\[.*?\])?\{.*?\}', '', latex_text)
        latex_text = re.sub(r'\\begin\{document\}', '', latex_text)
        latex_text = re.sub(r'\\end\{document\}', '', latex_text)
        
        latex_text = re.sub(r'\n{3,}', '\n\n', latex_text)
        latex_text = re.sub(r'(\\(?:begin|end)\{[^\}]*\})\n+', r'\1', latex_text)
        latex_text = re.sub(r'\n\s*\\item', r'\\item', latex_text)
        
        latex_text = re.sub(r'%.*?\n', '\n', latex_text)
        latex_text = latex_text.strip()

        return jsonify({'success': True, 'latex_text': latex_text})
    except Exception as e:
        import traceback
        print("Error converting to LaTeX:")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'image' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['image']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    folder = request.form.get('folder', 'temp')
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    rand_suffix = uuid.uuid4().hex[:6]
    filename = secure_filename(f"img_{timestamp}_{rand_suffix}.png")

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    temp_file_path = temp_file.name

    try:
        if Image and file.content_type.startswith('image/'):
            try:
                img = Image.open(file)
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                max_size = 1200
                if max(img.size) > max_size:
                    ratio = max_size / max(img.size)
                    img = img.resize((int(img.size[0] * ratio), int(img.size[1] * ratio)), Image.LANCZOS)
                img.save(temp_file_path, 'PNG', optimize=True)
                print(f"Image temporarily saved to {temp_file_path}")
            except Exception as e:
                print(f"Error processing image: {e}")
                file.save(temp_file_path)
        else:
            file.save(temp_file_path)

        temp_file.close()

        try:
            project_folder_id = find_or_create_folder(folder)
            file_id = find_file_in_folder(filename, project_folder_id)

            if file_id:
                media = MediaFileUpload(temp_file_path, mimetype='image/png')
                drive_client.files().update(
                    fileId=file_id,
                    media_body=media
                ).execute()
            else:
                file_metadata = {
                    'name': filename,
                    'parents': [project_folder_id]
                }
                media = MediaFileUpload(temp_file_path, mimetype='image/png')
                drive_client.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()

            file_path = f"{folder}/{filename}"
            return jsonify({
                'success': True,
                'filename': filename,
                'filepath': file_path
            })
        except Exception as e:
            print(f"❌ Error uploading image to Google Drive: {e}")
            return jsonify({'error': str(e)}), 500
    finally:
        import time
        time.sleep(0.1)
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                print(f"Deleted temporary file {temp_file_path}")
        except Exception as e:
            print(f"❌ Error deleting temporary file {temp_file_path}: {e}")

@app.route('/get-image/<path:filepath>')
def get_image(filepath):
    try:
        parts = filepath.split('/')
        if len(parts) < 2:
            return "Invalid filepath format", 400
        folder = '/'.join(parts[:-1])
        filename = parts[-1]

        project_folder_id = find_or_create_folder(folder)
        file_id = find_file_in_folder(filename, project_folder_id)
        if not file_id:
            return "Image not found", 404

        request = drive_client.files().get_media(fileId=file_id)
        file_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(file_stream, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        file_stream.seek(0)

        return send_file(
            file_stream,
            mimetype='image/png',
            as_attachment=False
        )
    except Exception as e:
        print(f"❌ Error retrieving image from Google Drive: {e}")
        return "Image not found", 404

@app.errorhandler(404)
def not_found(e):
    path = request.path
    
    if any(path.endswith(f'.{ext}') for ext in ALLOWED_EXTENSIONS):
        print(f"404 Error: Image not found at {path}")
        if path.startswith('/static/uploads/') and '/' in path[15:]:
            filename = path.split('/')[-1]
            if os.path.exists(os.path.join(app.static_folder, 'uploads', filename)):
                print(f"Found image at root uploads folder: {filename}")
                return redirect(url_for('get_image', filename=filename))
    
    return "File not found", 404

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'pdf', 'webp', 'bmp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/debug_latex_content/<filename>')
def debug_latex_content(filename):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM laporan WHERE filename = %s', (filename,))
            laporan = cursor.fetchone()
            if not laporan:
                return f"Metadata not found for {filename}", 404

            metadata = json.loads(laporan['metadata']) if laporan['metadata'] else {}
            cursor.execute('SELECT * FROM sections WHERE filename = %s', (filename,))
            sections = cursor.fetchall()
            dasar_teori_sections = {}
            main_sections = {}

            for section in sections:
                if section['type'] == 'dasar_teori':
                    section_id = section['section_id'].replace('dasar_teori_', '')
                    dasar_teori_sections[section_id] = {
                        'title': section['title'],
                        'content': section['content'],
                        'image': section['image']
                    }
                elif section['type'] == 'section':
                    main_sections[section['section_id']] = {
                        'type': 'section',
                        'title': section['title']
                    }
                elif section['type'] == 'subsection':
                    main_sections[section['section_id']] = {
                        'type': 'subsection',
                        'title': section['title'],
                        'code': section['content'],
                        'image': section['image'],
                        'parent_section': section['parent_section']
                    }
                elif section['type'] == 'penjelasan':
                    section_id = section['parent_section']
                    if section_id in main_sections:
                        main_sections[section_id]['penjelasan'] = section['content']

            metadata['dasar_teori_sections'] = dasar_teori_sections
            metadata['main_sections'] = main_sections
            metadata['tujuan'] = laporan['tujuan']
            metadata['kesimpulan'] = laporan['kesimpulan']
            metadata['referensi'] = laporan['referensi']

        output = []
        output.append(f"<h1>LaTeX Debug for {filename}</h1>")
        
        output.append("<h2>Dasar Teori Sections</h2>")
        output.append(f"<p>Total sections: {len(dasar_teori_sections)}</p>")
        
        for section_id, section in dasar_teori_sections.items():
            title = section.get('title', 'No title')
            content = section.get('content', '')
            backslash_count = content.count('\\')
            begin_count = content.count('\\begin{')
            end_count = content.count('\\end{')
            item_count = content.count('\\item')
            
            output.append(f"<h3>Section {section_id}: {title}</h3>")
            output.append(f"<p>Content length: {len(content)} chars</p>")
            output.append(f"<p>Backslashes: {backslash_count}, \\begin: {begin_count}, \\end: {end_count}, \\item: {item_count}</p>")
            
            content_html = content.replace('&', '&').replace('<', '<').replace('>', '>')
            output.append("<pre style='background:#f5f5f5;padding:10px;border:1px solid #ddd;white-space:pre-wrap'>" + content_html + "</pre>")
            
        output.append("<h2>Main Sections</h2>")
        output.append(f"<p>Total sections: {len(main_sections)}</p>")
        
        for section_id, section in main_sections.items():
            section_type = section.get('type', 'unknown')
            title = section.get('title', 'No title')
            
            output.append(f"<h3>{section_type.capitalize()} {section_id}: {title}</h3>")
            
            if section_type == 'subsection':
                code = section.get('code', '')
                penjelasan = section.get('penjelasan', '')
                
                output.append(f"<h4>Code ({len(code)} chars)</h4>")
                code_html = code.replace('&', '&').replace('<', '<').replace('>', '>')
                output.append("<pre style='background:#f5f5f5;padding:10px;border:1px solid #ddd;white-space:pre-wrap'>" + code_html + "</pre>")
                
                output.append(f"<h4>Penjelasan ({len(penjelasan)} chars)</h4>")
                penjelasan_html = penjelasan.replace('&', '&').replace('<', '<').replace('>', '>')
                output.append("<pre style='background:#f5f5f5;padding:10px;border:1px solid #ddd;white-space:pre-wrap'>" + penjelasan_html + "</pre>")
                
        return "".join(output)
        
    except Exception as e:
        import traceback
        error_html = f"<h1>Error</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>"
        return error_html

if __name__ == '__main__':
    app.run(debug=True)

application = app