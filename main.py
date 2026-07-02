import streamlit as st
import PyPDF2
import google.generativeai as genai
import requests
import base64

# =====================================================================
# CONFIGURATION & PAGE SETUP
# =====================================================================
st.set_page_config(page_title="MathQuiz AI", page_icon="🧮", layout="wide")

st.title("🧮 MathQuiz AI")
st.subheader("Otomatisasi Pembuatan Dokumen Soal Matematika Siap Cetak")
st.write("Selamat datang! Unggah materi kuliah/sekolah Anda, dan biarkan AI menyusun dokumen ujian berstandar LaTeX untuk Anda.")

# =====================================================================
# SIDEBAR: KONTROL PARAMETER SOAL
# =====================================================================
st.sidebar.header("⚙️ Pengaturan Ujian")

tingkat_pendidikan = st.sidebar.selectbox(
    "Tingkat Pendidikan:",
    ["SMP", "SMA", "Perguruan Tinggi"]
)

jumlah_soal = st.sidebar.slider("Jumlah Soal:", min_value=5, max_value=30, value=10, step=5)

api_key_input = st.sidebar.text_input("Masukkan Gemini API Key Anda:", type="password")

# =====================================================================
# MAIN INTERFACE: INPUT MATERI
# =====================================================================
st.write("---")
st.markdown("### 📥 Langkah 1: Unggah Materi Pembelajaran")

uploaded_files = st.file_uploader(
    "Pilih satu atau beberapa file materi (PDF atau TXT):", 
    type=["pdf", "txt"], 
    accept_multiple_files=True
)

teks_tambahan = st.text_area("Atau tempelkan (paste) teks materi tambahan di sini (optional):")

# Inisialisasi session state agar data tidak hilang saat halaman di-reload
if 'final_pdf_bytes' not in st.session_state:
    st.session_state['final_pdf_bytes'] = None
if 'generated_questions' not in st.session_state:
    st.session_state['generated_questions'] = None

# =====================================================================
# PROSES TOMBOL GENERATE
# =====================================================================
st.write("---")
st.markdown("### ⚙️ Langkah 2: Eksekusi")

if st.button("🚀 Generate Dokumen Soal Sekarang", type="primary"):
    if not uploaded_files and not teks_tambahan:
        st.warning("Mohon unggah file materi atau masukkan teks materi terlebih dahulu!")
    elif not api_key_input:
        st.warning("Mohon masukkan Gemini API Key Anda di sidebar sebelah kiri!")
    else:
        genai.configure(api_key=api_key_input)
        
        with st.spinner("Membaca data materi kuliah... Mohon tunggu..."):
            materi_gabungan = ""
            for file in uploaded_files:
                if file.name.endswith('.pdf'):
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        materi_gabungan += page.extract_text() + "\n"
                elif file.name.endswith('.txt'):
                    materi_gabungan += file.read().decode("utf-8") + "\n"
            
            if teks_tambahan:
                materi_gabungan += teks_tambahan

        # SYSTEM PROMPT: Mengunci keluaran agar berupa kode LaTeX murni yang valid
        system_prompt = f"""
        Anda adalah seorang pakar pembuat soal matematika dan instruktur LaTeX profesional.
        Tugas Anda adalah menghasilkan dokumen teks dokumen LaTeX UTUH (valid document) yang siap dikompilasi menjadi PDF lembar ujian resmi.
        
        Aturan Struktur Dokumen LaTeX:
        - Wajib diawali dengan '\\documentclass{{article}}' dan dibungkus di dalam '\\begin{{document}}' dan '\\end{{document}}'.
        - Buat kop ujian sederhana di bagian atas berisi: Nama Sekolah/Kampus, Mata Pelajaran/Kuliah, Alokasi Waktu, Lembar Nama Siswa, dan Kelas.
        - Gunakan paket standar seperti '\\usepackage{{amsmath, amssymb, amsfonts}}' untuk mendukung visual rumus eksakta.
        
        Aturan Konten Soal:
        1. Buat tepat {jumlah_soal} soal pilihan ganda (A, B, C, D, E) berdasarkan materi referensi yang diberikan.
        2. Sesuaikan bobot tingkat kesulitan untuk skala {tingkat_pendidikan}.
        3. Semua simbol, angka, rumus, pecahan, akar, dan variabel matematika WAJIB ditulis dalam format LaTeX murni menggunakan pembungkus '$...$' atau '$$...$$'.
        4. Pisahkan kunci jawaban dengan jelas di halaman paling akhir (Gunakan '\\newpage' sebelum bagian Kunci Jawaban).
        
        PENTING: Jangan berikan teks pembuka atau penutup di luar blok kode LaTeX. Berikan HANYA kode LaTeX murni dari \\documentclass sampai \\end{{document}}.
        """

        with st.spinner("AI Gemini sedang menyusun dokumen lembar ujian berstandar LaTeX..."):
            try:
                model = genai.GenerativeModel('gemma-4-31b-it')
                response = model.generate_content([system_prompt, f"Materi Referensi:\n{materi_gabungan}"])
                
                raw_text = response.text
                
                # ----------------=============================================
                # STRATEGI PEMBERSIHAN TOTAL TEXT SAMPAH
                # ----------------=============================================
                clean_latex = raw_text.replace("```latex", "").replace("```", "").strip()
                
                # Menggunakan indeks baris paling bersih untuk menemukan titik awal document class yang murni
                if "\\documentclass" in clean_latex:
                    # Cari semua kemunculan \documentclass, ambil yang paling terakhir mendekati \begin{document}
                    parts = clean_latex.split("\\documentclass")
                    # Rekonstruksi struktur dengan mengambil bagian kode yang paling utuh di akhir
                    clean_latex = "\\documentclass" + parts[-1]
                
                st.session_state['generated_questions'] = clean_latex
                
                # ----------------=============================================
                # INTEGRASI FORMATED IO API (MICROSERVICES)
                # ----------------=============================================
                with st.spinner("Mengirim kode ke FormATeX API untuk di-render menjadi PDF profesional..."):
                    url_api = "https://api.formatex.io/api/v1/compile"
                    headers = {"X-API-Key": "fex_85e6ce2e63b5376224aa4ff190f8d9060077b287e536664c342d9b37de9d672a"}
                    payload = {
                        "engine": "xelatex",
                        "latex": clean_latex
                    }
                    
                    res = requests.post(url_api, headers=headers, json=payload)
                    
                    if res.status_code == 200 and b'%PDF' in res.content[:10]:
                        st.session_state['final_pdf_bytes'] = res.content
                        st.success("🎉 Dokumen PDF Berhasil Dibuat!")
                    else:
                        st.session_state['final_pdf_bytes'] = None
                        st.error(f"Gagal mengonversi LaTeX menjadi PDF. Status Code: {res.status_code}. Server mendeteksi kesalahan sintaks.")
                        
            except Exception as e:
                st.error(f"Terjadi kesalahan pada sistem: {e}")

# =====================================================================
# TAMPILAN OUTPUT BARU: PDF PREVIEW NATIVE (TIDAK ADA TEKS BERANTAK)
# =====================================================================
if st.session_state['final_pdf_bytes']:
    st.write("---")
    st.markdown("### 📄 Hasil Dokumen Ujian Siap Cetak")
    
    # 1. Tombol Download yang Nyaman
    st.download_button(
        label="📥 Download PDF Sekarang",
        data=st.session_state['final_pdf_bytes'],
        file_name="MathQuiz_Dokumen_Ujian.pdf",
        mime="application/pdf",
        type="primary"
    )
    
    st.write("")
    st.write("#### 👁️ Preview Dokumen Resmi:")
    
    # 2. Logika Menyematkan PDF Viewer Menggunakan Tag HTML iframe & Base64
    #    Ini akan menampilkan dokumen lembar ujian asli langsung di halaman web tanpa teks mentah!
    base64_pdf = base64.b64encode(st.session_state['final_pdf_bytes']).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
    
    # Render komponen visual ke antarmuka Streamlit
    st.markdown(pdf_display, unsafe_allow_html=True)