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

try:
    from PIL import Image
except ImportError:
    print("WARNING: PIL/Pillow not installed. Image processing will be limited.")
    Image = None

load_dotenv()

# Gemini API key
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_AVAILABLE = True  # Asumsi GEMINI_AVAILABLE sudah didefinisikan, misalnya True jika API tersedia

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

# Inisialisasi model Gemini
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
app.secret_key = secrets.token_hex(16)  # Menghasilkan 32 karakter heksadesimal
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

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
    """Mendapatkan daftar filename dari folder uploads berdasarkan metadata.json"""
    uploads_dir = os.path.join(app.config['UPLOAD_FOLDER'])
    if not os.path.exists(uploads_dir):
        return []
    filenames = [
        {
            'filename': f,
            'nama': '',
            'judul': '',
            'matkul': '',
            'tanggal': '',
            'last_modified': os.path.getmtime(os.path.join(uploads_dir, f, "metadata.json"))
        }
        for f in os.listdir(uploads_dir)
        if os.path.isdir(os.path.join(uploads_dir, f)) and os.path.exists(os.path.join(uploads_dir, f, "metadata.json"))
    ]
    filenames.sort(key=lambda x: x['last_modified'], reverse=True)
    return filenames

def save_latex_to_txt_file(filename, content, section_id):
    """Simpan konten LaTeX ke file .txt dengan mempertahankan format paragraf"""
    project_dir = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    os.makedirs(project_dir, exist_ok=True)
    file_path = os.path.join(project_dir, f"{section_id}_raw.txt")
    
    try:
        # Pertahankan format paragraf yang benar
        content = re.sub(r'\n{3,}', '\n\n', content)
        if '\n\n' not in content and len(content) > 100:
            content = re.sub(r'(\.\s+)([A-Z])', r'\1\n\n\2', content)
        content = re.sub(r'(\\end\{[^}]+\})(\S)', r'\1\n\n\2', content)
        content = re.sub(r'(\S)(\\begin\{[^}]+\})', r'\1\n\n\2', content)
        content = re.sub(r'(\\item[^\n]+)\n(?!\\item|\\end)', r'\1\n\n', content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        backslash_count = content.count('\\')
        paragraph_count = content.count('\n\n') + 1
        print(f"✓ LaTeX content saved to {file_path}: {len(content)} chars, {backslash_count} backslashes, {paragraph_count} paragraphs")
        return True
    except Exception as e:
        print(f"❌ Error saving LaTeX content to {file_path}: {str(e)}")
        return False

def read_latex_from_txt_file(filename, section_id):
    """Membaca konten LaTeX dari file .txt dengan mempertahankan format"""
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename, f"{section_id}_raw.txt")
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return ""
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        backslash_count = content.count('\\')
        paragraph_count = content.count('\n\n') + 1
        print(f"✓ Read LaTeX from {file_path}: {len(content)} chars, {backslash_count} backslashes, {paragraph_count} paragraphs")
        return content
    except Exception as e:
        print(f"❌ Error reading file {file_path}: {e}")
        return ""

def save_metadata_json(filename, data):
    """Simpan metadata ke file JSON"""
    project_dir = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    os.makedirs(project_dir, exist_ok=True)
    file_path = os.path.join(project_dir, "metadata.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Metadata saved to {file_path}")

def read_metadata_json(filename):
    """Baca metadata dari file JSON"""
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename, "metadata.json")
    if not os.path.exists(file_path):
        print(f"Warning: Metadata file {file_path} not found")
        return {}
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

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
    # Hanya ambil baris yang tidak kosong dan langsung masukkan isinya
    items = [line.strip() for line in lines if line.strip()]
    return '\n'.join(items) if items else '-'

def generate_latex_for_dasar_teori(sections, filename):
    """Generate LaTeX untuk dasar teori"""
    if not sections:
        return ""
        
    print(f"Generating LaTeX for {len(sections)} dasar teori sections")
    content = ""  # Menghapus \section{Dasar Teori}
    
    # Debug total sections
    print(f"Dasar teori sections: {list(sections.keys())}")
    
    for section_id, section in sorted(sections.items(), key=lambda x: int(x[0]) if x[0].isdigit() else float('inf')):
        title = section.get('title', '')
        print(f"Processing dasar teori section {section_id}: {title}")
        
        # Baca konten langsung dari file
        raw_content = read_latex_from_txt_file(filename, f"dasar_teori_{section_id}")
        
        if not raw_content:
            print(f"WARNING: No content found for dasar teori section {section_id}")
            # Alternatif coba baca dari metadata
            if 'content' in section:
                raw_content = section['content']
                print(f"Using content from metadata for section {section_id}")
        
        image = section.get('image', '')
        
        # Log statistik konten untuk debugging
        if raw_content:
            print(f"Section {section_id} content: {len(raw_content)} chars, {raw_content.count('\\')} backslashes")
        else:
            print(f"Section {section_id} has no content!")
        
        # Tambahkan title sebagai section (bukan subsection)
        if title:
            content += f"\\section{{{title}}}\n"  # Mengubah \subsection menjadi \section
        
        # Tambahkan konten jika ada
        if raw_content:
            content += raw_content + "\n\n"
            
            # Periksa apakah konten memiliki format LaTeX yang benar
            if "begin{" in raw_content and "\\begin{" not in raw_content:
                print(f"WARNING: LaTeX tags missing backslashes in section {section_id}")
                
        # Tambahkan gambar jika ada
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

def generate_latex_for_sections(sections, filename=None):
    """Generate LaTeX untuk hasil dan pembahasan"""
    if not sections:
        return ""
        
    print(f"Generating LaTeX for {len(sections)} sections")
    latex = ""
    section_groups = {}
    
    # Group sections by parent
    for id, data in sections.items():
        if data.get('type') == 'section':
            section_groups[id] = {'title': data['title'], 'subsections': []}
            print(f"Found main section {id}: {data['title']}")
            
    # Add subsections to their parents
    for id, data in sections.items():
        if data.get('type') == 'subsection':
            parent_id = data.get('parent_section', next(iter(section_groups)) if section_groups else 'default')
            if parent_id not in section_groups:
                section_groups[parent_id] = {'title': 'Latihan', 'subsections': []}
                print(f"Created default parent section for subsection {id}")
                
            # Read content directly if filename provided
            code_content = ""
            penjelasan_content = ""
            
            if filename:
                code_content = read_latex_from_txt_file(filename, f"code_{id}")
                penjelasan_content = read_latex_from_txt_file(filename, f"penjelasan_{id}")
                print(f"Read content for subsection {id}: code={len(code_content)} chars, penjelasan={len(penjelasan_content)} chars")
            
            section_groups[parent_id]['subsections'].append({
                'id': id,
                'title': data['title'], 
                'code': code_content or data.get('code', ''),
                'image': data.get('image', ''),
                'penjelasan': penjelasan_content or data.get('penjelasan', '')
            })
            print(f"Added subsection {id} to parent {parent_id}")
    
    # Generate LaTeX for each section group
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
        # Ambil data dari form dan hapus spasi kosong di awal/akhir
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

        # Fungsi untuk membersihkan teks: hapus spasi di awal/akhir dan baris kosong berlebih
        def clean_text(text):
            if not text:
                return ''
            # Hapus spasi di awal dan akhir
            text = text.strip()
            # Ganti multiple newlines dengan single newline
            text = re.sub(r'\n\s*\n+', '\n', text)
            return text

        # Terapkan pembersihan teks pada field yang relevan
        tujuan = clean_text(tujuan)
        kesimpulan = clean_text(kesimpulan)
        referensi = clean_text(referensi)

        # Validasi data wajib
        if not all([nama, npm, matkul, judul]):
            flash('Nama, NPM, Mata Kuliah, dan Judul harus diisi!', 'error')
            return render_template('form.html', form_data=request.form, matkul_dosen=MATKUL_DOSEN, filenames=get_filenames())

        # Tentukan filename dan folder proyek
        filename = standardize_filename(nama, npm, matkul, judul)
        project_dir = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(project_dir, exist_ok=True)

        # Process Dasar Teori Sections
        dasar_teori_sections = {}
        for key in request.form:
            if key.startswith('dasar_teori_section_id_'):
                section_id = request.form[key]
                content_key = f'dasar_teori_section_content_{section_id}'
                raw_content = request.form.get(content_key, '').strip()
                raw_content = clean_text(raw_content)  # Bersihkan teks
                # Simpan konten ke file teks
                save_latex_to_txt_file(filename, raw_content, f"dasar_teori_{section_id}")
                dasar_teori_sections[section_id] = {
                    'title': request.form.get(f'dasar_teori_section_title_{section_id}', '').strip(),
                    'content': raw_content,  # Simpan juga di metadata sebagai fallback
                    'content_file': f"dasar_teori_{section_id}_raw.txt",
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
                    code_content = clean_text(code_content)  # Bersihkan teks
                    penjelasan_content = clean_text(penjelasan_content)  # Bersihkan teks
                    if parent_key in request.form:
                        main_sections[section_id]['parent_section'] = request.form[parent_key]
                    if code_key in request.form:
                        save_latex_to_txt_file(filename, code_content, f"code_{section_id}")
                        main_sections[section_id]['code'] = code_content  # Simpan juga di metadata
                        main_sections[section_id]['code_file'] = f"code_{section_id}_raw.txt"
                    if penjelasan_key in request.form:
                        save_latex_to_txt_file(filename, penjelasan_content, f"penjelasan_{section_id}")
                        main_sections[section_id]['penjelasan'] = penjelasan_content  # Simpan juga di metadata
                        main_sections[section_id]['penjelasan_file'] = f"penjelasan_{section_id}_raw.txt"
                    main_sections[section_id]['image'] = request.form.get(f'image_{section_id}', '').strip()

        # Save additional sections
        save_latex_to_txt_file(filename, tujuan, "tujuan")
        save_latex_to_txt_file(filename, kesimpulan, "kesimpulan")
        save_latex_to_txt_file(filename, referensi, "referensi")

        # Save metadata
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
        save_metadata_json(filename, metadata)

        # Jika edit mode, salin file gambar dari folder lama
        if edit_mode and original_filename and original_filename != filename:
            old_dir = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
            if os.path.exists(old_dir):
                for item in os.listdir(old_dir):
                    if item.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg')) or 'lambang' in item.lower():
                        shutil.copy2(os.path.join(old_dir, item), os.path.join(project_dir, item))

        session['last_filename'] = filename
        flash('Data tersimpan sukses!', 'success')
        return redirect(url_for('edit', filename=filename) if action == 'save' else url_for('generate_latex', filename=filename))

    # Logika untuk GET
    last_filename = session.get('last_filename')
    if last_filename and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], last_filename)):
        metadata = read_metadata_json(last_filename)
        for section_id in metadata.get('dasar_teori_sections', {}):
            content = read_latex_from_txt_file(last_filename, f"dasar_teori_{section_id}")
            metadata['dasar_teori_sections'][section_id]['content'] = content.strip() if content else ''
        for section_id in metadata.get('main_sections', {}):
            if metadata['main_sections'][section_id]['type'] == 'subsection':
                code = read_latex_from_txt_file(last_filename, f"code_{section_id}")
                penjelasan = read_latex_from_txt_file(last_filename, f"penjelasan_{section_id}")
                metadata['main_sections'][section_id]['code'] = code.strip() if code else ''
                metadata['main_sections'][section_id]['penjelasan'] = penjelasan.strip() if penjelasan else ''
        metadata['tujuan'] = read_latex_from_txt_file(last_filename, "tujuan").strip()
        metadata['kesimpulan'] = read_latex_from_txt_file(last_filename, "kesimpulan").strip()
        metadata['referensi'] = read_latex_from_txt_file(last_filename, "referensi").strip()
        flash(f'Melanjutkan pengeditan {last_filename}', 'info')
        return render_template('form.html', form_data=metadata, matkul_dosen=MATKUL_DOSEN, filenames=get_filenames())
    return render_template('form.html', form_data=None, matkul_dosen=MATKUL_DOSEN, filenames=get_filenames())

@app.route('/edit/<filename>')
def edit(filename):
    """Edit laporan dengan filename yang ditentukan"""
    try:
        # Baca metadata dari file
        metadata = read_metadata_json(filename)
        if not metadata:
            flash(f'File {filename} tidak ditemukan', 'error')
            return redirect('/')
            
        print(f"Loading edit form for {filename}")
        print(f"Metadata keys: {list(metadata.keys())}")
        
        # Pastikan metadata memiliki struktur yang diharapkan
        if 'dasar_teori_sections' not in metadata:
            print(f"WARNING: Missing dasar_teori_sections in metadata for {filename}")
            metadata['dasar_teori_sections'] = {}
            
        if 'main_sections' not in metadata:
            print(f"WARNING: Missing main_sections in metadata for {filename}")
            metadata['main_sections'] = {}
            
        # Load dasar teori section contents
        for section_id, section in metadata['dasar_teori_sections'].items():
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename, f"dasar_teori_{section_id}_raw.txt")
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    section['content'] = content
                    print(f"✓ Loaded dasar teori section {section_id}: {len(content)} chars")
                except Exception as e:
                    print(f"❌ Error loading dasar teori section {section_id}: {str(e)}")
                    section['content'] = ""
            else:
                print(f"❌ File not found: {file_path}")
                section['content'] = section.get('content', '')  # Fallback ke metadata jika ada

        # Load main sections (code & penjelasan)
        for section_id, section in metadata['main_sections'].items():
            if section.get('type') == 'subsection':
                # Load code
                code_path = os.path.join(app.config['UPLOAD_FOLDER'], filename, f"code_{section_id}_raw.txt")
                if os.path.exists(code_path):
                    try:
                        with open(code_path, 'r', encoding='utf-8') as f:
                            code = f.read()
                        section['code'] = code
                    except Exception as e:
                        print(f"❌ Error loading code for {section_id}: {str(e)}")
                        section['code'] = section.get('code', '')  # Fallback ke metadata jika ada
                else:
                    print(f"❌ Code file not found: {code_path}")
                    section['code'] = section.get('code', '')

                # Load penjelasan
                penjelasan_path = os.path.join(app.config['UPLOAD_FOLDER'], filename, f"penjelasan_{section_id}_raw.txt")
                if os.path.exists(penjelasan_path):
                    try:
                        with open(penjelasan_path, 'r', encoding='utf-8') as f:
                            penjelasan = f.read()
                        section['penjelasan'] = penjelasan
                    except Exception as e:
                        print(f"❌ Error loading penjelasan for {section_id}: {str(e)}")
                        section['penjelasan'] = section.get('penjelasan', '')  # Fallback ke metadata jika ada
                else:
                    print(f"❌ Penjelasan file not found: {penjelasan_path}")
                    section['penjelasan'] = section.get('penjelasan', '')

                print(f"Section {section_id}: code={len(section.get('code', ''))}, penjelasan={len(section.get('penjelasan', ''))}")

        # Load other content
        for content_type in ['tujuan', 'kesimpulan', 'referensi']:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename, f"{content_type}_raw.txt")
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    metadata[content_type] = content
                    print(f"✓ Loaded {content_type}: {len(content)} chars")
                except Exception as e:
                    print(f"❌ Error loading {content_type}: {str(e)}")
                    metadata[content_type] = ""
            else:
                print(f"❌ File not found: {file_path}")
                metadata[content_type] = ""

        # Set active session
        session['last_filename'] = filename
        
        # Debug: Verifikasi data yang akan dikirim ke template
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
    """Generate LaTeX document from file content"""
    print(f"Generating LaTeX for {filename}")
    
    try:
        # Baca metadata dari file
        metadata = read_metadata_json(filename)
        if not metadata:
            flash(f'File {filename} tidak ditemukan', 'error')
            return redirect('/')
            
        # Process template
        latex_content = LATEX_TEMPLATE
        
        # Baca dasar teori dari file teks
        dasar_teori_sections = metadata.get('dasar_teori_sections', {})
        sections = metadata.get('main_sections', {})
        
        # Project folder path
        project_dir = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(project_dir, exist_ok=True)
        
        # Add logo if needed
        logo_path = os.path.join(project_dir, 'lambang ugm.png')
        if not os.path.exists(logo_path):
            default_logo = os.path.join(app.static_folder, 'lambang ugm.png')
            if os.path.exists(default_logo):
                shutil.copy(default_logo, logo_path)
        
        # Debug untuk dasar teori
        print(f"Found {len(dasar_teori_sections)} dasar teori sections")
        for id, section in dasar_teori_sections.items():
            content = read_latex_from_txt_file(filename, f"dasar_teori_{id}")
            backslash_count = content.count('\\')
            print(f"Section {id}: title='{section.get('title')}', content={len(content)} chars, backslashes={backslash_count}")
            
        # Debug untuk sections
        print(f"Found {len(sections)} sections")
        
        # Generate sections content
        dasar_teori_latex = generate_latex_for_dasar_teori(dasar_teori_sections, filename)
        print(f"Generated dasar teori LaTeX: {len(dasar_teori_latex)} chars")
        
        hasil_pembahasan_latex = generate_latex_for_sections(sections, filename)
        print(f"Generated hasil pembahasan LaTeX: {len(hasil_pembahasan_latex)} chars")
        
        # Basic replacements
        replacements = {
            'MATKUL': metadata.get('matkul', ''),
            'PERTEMUAN': metadata.get('pertemuan', ''),
            'JUDUL': metadata.get('judul', ''),
            'TANGGAL': metadata.get('tanggal', ''),
            'NAMA': metadata.get('nama', ''),
            'NPM': metadata.get('npm', ''),
            'KELAS': metadata.get('kelas', ''),
            'DOSEN': metadata.get('dosen', ''),
            'TUJUAN': process_tujuan(read_latex_from_txt_file(filename, "tujuan") or metadata.get('tujuan', '')),
            'DASAR_TEORI': dasar_teori_latex,
            'HASIL_PEMBAHASAN': hasil_pembahasan_latex,
            'KESIMPULAN': read_latex_from_txt_file(filename, "kesimpulan") or metadata.get('kesimpulan', ''),
            'REFERENSI': process_referensi(read_latex_from_txt_file(filename, "referensi") or metadata.get('referensi', ''))
        }
        
        # Apply all replacements
        for key, value in replacements.items():
            if value is None:
                value = ''
            latex_content = latex_content.replace(key, value)
            print(f"Replaced {key} with {len(value)} chars")
        
        # Save LaTeX content to file
        tex_file = os.path.join(project_dir, f"{filename}.tex")
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(latex_content)
        print(f"Saved LaTeX content to {tex_file}")
        
        # Collect images used in the document
        images = []
        # From dasar teori sections
        for section in dasar_teori_sections.values():
            if section.get('image'):
                images.append({'name': os.path.basename(section['image'])})
        # From main sections
        for section in sections.values():
            if section.get('type') == 'subsection' and section.get('image'):
                images.append({'name': os.path.basename(section['image'])})
        # Add logo
        if os.path.exists(logo_path):
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
    """Download all images as a ZIP file"""
    project_dir = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(project_dir):
        flash(f'Project folder {filename} not found', 'error')
        return redirect(url_for('edit', filename=filename))
    
    # Collect all images
    images = []
    # From metadata
    metadata = read_metadata_json(filename)
    for section in metadata.get('dasar_teori_sections', {}).values():
        if section.get('image'):
            images.append(section['image'])
    for section in metadata.get('main_sections', {}).values():
        if section.get('type') == 'subsection' and section.get('image'):
            images.append(section['image'])
    # Add logo
    logo_path = os.path.join(project_dir, 'lambang ugm.png')
    if os.path.exists(logo_path):
        images.append('lambang ugm.png')
    
    if not images:
        flash('No images found to download', 'error')
        return redirect(url_for('generate_latex', filename=filename))
    
    # Create a ZIP file in memory
    memory_file = io.BytesIO()
    with ZipFile(memory_file, 'w') as zf:
        for image in images:
            image_path = os.path.join(project_dir, os.path.basename(image))
            if os.path.exists(image_path):
                zf.write(image_path, os.path.basename(image))
    
    memory_file.seek(0)
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f"{filename}_images.zip"
    )

@app.route('/download_tex/<filename>')
def download_tex(filename):
    tex_file = os.path.join(app.config['UPLOAD_FOLDER'], filename, f"{filename}.tex")
    if os.path.exists(tex_file):
        return send_file(tex_file, as_attachment=True, download_name=f"{filename}.tex")
    flash('File LaTeX tidak ditemukan', 'error')
    return redirect(url_for('edit', filename=filename))

# Tambahan route lain yang diperlukan
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
        # Prompt yang lebih spesifik untuk menghindari template LaTeX
        prompt = (f"Convert the following text to LaTeX format, but DO NOT include any LaTeX document "
                 f"preamble (no \\documentclass, \\usepackage, \\begin{{document}}, etc). "
                 f"Just provide the content LaTeX commands:\n\n{text}\n\n"
                 f"Ensure the output uses proper LaTeX syntax like \\section, \\textbf, \\item, etc. "
                 f"Do not add any document structure commands.")
        if preserve:
            prompt += "\nPreserve the original formatting as much as possible."

        # Panggil API Gemini
        response = model.generate_content(prompt)
        latex_text = response.text.strip()

        # Bersihkan output dari preamble LaTeX yang mungkin masih ada
        import re
        
        # Hapus bagian preamble LaTeX jika masih ada
        latex_text = re.sub(r'\\documentclass(\[.*?\])?\{.*?\}', '', latex_text)
        latex_text = re.sub(r'\\usepackage(\[.*?\])?\{.*?\}', '', latex_text)
        latex_text = re.sub(r'\\begin\{document\}', '', latex_text)
        latex_text = re.sub(r'\\end\{document\}', '', latex_text)
        
        # Bersihkan teks LaTeX dari newline berlebih
        latex_text = re.sub(r'\n{3,}', '\n\n', latex_text)  # Kurangi multiple newlines
        latex_text = re.sub(r'(\\(?:begin|end)\{[^\}]*\})\n+', r'\1', latex_text)  # Hapus newline setelah \begin atau \end
        latex_text = re.sub(r'\n\s*\\item', r'\\item', latex_text)  # Hapus newline sebelum \item
        
        # Hapus komentar LaTeX
        latex_text = re.sub(r'%.*?\n', '\n', latex_text)
        
        # Hapus whitespace berlebih di awal dan akhir
        latex_text = latex_text.strip()

        return jsonify({'success': True, 'latex_text': latex_text})
    except Exception as e:
        import traceback
        print("Error converting to LaTeX:")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload with proper path construction"""
    if 'image' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    # Get the folder to save to (project folder)
    folder = request.form.get('folder', 'temp')
    
    # Ensure folder exists
    upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], folder)
    os.makedirs(upload_folder, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    rand_suffix = uuid.uuid4().hex[:6]  # Add randomness to prevent collisions
    filename = secure_filename(f"img_{timestamp}_{rand_suffix}.png")
    filepath = os.path.join(upload_folder, filename)
    
    # Process and save image
    if Image and file.content_type.startswith('image/'):
        try:
            img = Image.open(file)
            # Convert to RGB if needed (in case of transparent PNGs)
            if img.mode == 'RGBA':
                img = img.convert('RGB')
                
            # Resize if too large
            max_size = 1200
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                img = img.resize((int(img.size[0] * ratio), int(img.size[1] * ratio)), Image.LANCZOS)
                
            # Save with optimization
            img.save(filepath, 'PNG', optimize=True)
            print(f"Image saved to {filepath}")
        except Exception as e:
            print(f"Error processing image: {e}")
            file.save(filepath)
    else:
        file.save(filepath)
    
    # Return proper relative URL path that includes the folder
    file_url = f"/static/uploads/{folder}/{filename}"
    
    return jsonify({
        'success': True,
        'filename': filename,
        'filepath': file_url  # This is what frontend should use
    })

@app.route('/get-image/<filename>')
def get_image(filename):
    """Find image in various possible locations"""
    # Try direct path first (for backward compatibility)
    direct_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.isfile(direct_path):
        return send_file(direct_path)
    
    # Try in each project folder
    projects_dir = app.config['UPLOAD_FOLDER']
    for project in os.listdir(projects_dir):
        project_path = os.path.join(projects_dir, project)
        if os.path.isdir(project_path):
            img_path = os.path.join(project_path, filename)
            if os.path.isfile(img_path):
                return send_file(img_path)
    
    # Image not found
    return "Image not found", 404

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors with better info"""
    path = request.path
    
    # Check if this is an image request
    if any(path.endswith(f'.{ext}') for ext in ALLOWED_EXTENSIONS):
        # Log info to help debug
        print(f"404 Error: Image not found at {path}")
        
        # If it's in static/uploads but missing folder, try to locate it
        if path.startswith('/static/uploads/') and '/' in path[15:]:
            filename = path.split('/')[-1]
            if os.path.exists(os.path.join(app.static_folder, 'uploads', filename)):
                print(f"Found image at root uploads folder: {filename}")
                # Redirect to image finder
                return redirect(url_for('get_image', filename=filename))
    
    return "File not found", 404

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'pdf', 'webp', 'bmp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/debug_latex_content/<filename>')
def debug_latex_content(filename):
    """Debug LaTeX content for troubleshooting"""
    try:
        metadata = read_metadata_json(filename)
        if not metadata:
            return f"Metadata not found for {filename}", 404
            
        output = []
        output.append(f"<h1>LaTeX Debug for {filename}</h1>")
        
        # Debug dasar teori
        output.append("<h2>Dasar Teori Sections</h2>")
        dasar_teori_sections = metadata.get('dasar_teori_sections', {})
        output.append(f"<p>Total sections: {len(dasar_teori_sections)}</p>")
        
        for section_id, section in dasar_teori_sections.items():
            title = section.get('title', 'No title')
            content = read_latex_from_txt_file(filename, f"dasar_teori_{section_id}")
            backslash_count = content.count('\\')
            begin_count = content.count('\\begin{')
            end_count = content.count('\\end{')
            item_count = content.count('\\item')
            
            output.append(f"<h3>Section {section_id}: {title}</h3>")
            output.append(f"<p>Content length: {len(content)} chars</p>")
            output.append(f"<p>Backslashes: {backslash_count}, \\begin: {begin_count}, \\end: {end_count}, \\item: {item_count}</p>")
            
            # Show content with escaped HTML
            content_html = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            output.append("<pre style='background:#f5f5f5;padding:10px;border:1px solid #ddd;white-space:pre-wrap'>" + content_html + "</pre>")
            
            # Show raw file path
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename, f"dasar_teori_{section_id}_raw.txt")
            output.append(f"<p>File path: {file_path} (Exists: {os.path.exists(file_path)})</p>")
            
        # Debug hasil dan pembahasan
        output.append("<h2>Main Sections</h2>")
        main_sections = metadata.get('main_sections', {})
        output.append(f"<p>Total sections: {len(main_sections)}</p>")
        
        for section_id, section in main_sections.items():
            section_type = section.get('type', 'unknown')
            title = section.get('title', 'No title')
            
            output.append(f"<h3>{section_type.capitalize()} {section_id}: {title}</h3>")
            
            if section_type == 'subsection':
                code = read_latex_from_txt_file(filename, f"code_{section_id}")
                penjelasan = read_latex_from_txt_file(filename, f"penjelasan_{section_id}")
                
                output.append(f"<h4>Code ({len(code)} chars)</h4>")
                code_html = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                output.append("<pre style='background:#f5f5f5;padding:10px;border:1px solid #ddd;white-space:pre-wrap'>" + code_html + "</pre>")
                
                output.append(f"<h4>Penjelasan ({len(penjelasan)} chars)</h4>")
                penjelasan_html = penjelasan.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                output.append("<pre style='background:#f5f5f5;padding:10px;border:1px solid #ddd;white-space:pre-wrap'>" + penjelasan_html + "</pre>")
                
                # Show file paths
                code_path = os.path.join(app.config['UPLOAD_FOLDER'], filename, f"code_{section_id}_raw.txt")
                penjelasan_path = os.path.join(app.config['UPLOAD_FOLDER'], filename, f"penjelasan_{section_id}_raw.txt")
                
                output.append(f"<p>Code file: {code_path} (Exists: {os.path.exists(code_path)})</p>")
                output.append(f"<p>Penjelasan file: {penjelasan_path} (Exists: {os.path.exists(penjelasan_path)})</p>")
                
        # Test LaTeX generation
        output.append("<h2>Test LaTeX Generation</h2>")
        output.append("<form method='post' action='/test_latex_generation'>")
        output.append(f"<input type='hidden' name='filename' value='{filename}'>")
        output.append("<button type='submit' style='background:#007bff;color:white;padding:10px 20px;border:none;cursor:pointer;margin-top:10px'>Generate Test LaTeX</button>")
        output.append("</form>")
        
        return "".join(output)
        
    except Exception as e:
        import traceback
        error_html = f"<h1>Error</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>"
        return error_html

if __name__ == '__main__':
    app.run(debug=True)

application = app