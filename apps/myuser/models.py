from django.db import models
from django.conf import settings

class BRSExcel(models.Model):
    id_brsexcel = models.AutoField(primary_key=True)
    judul_brs = models.CharField(max_length=250, null=False)
    id_file = models.CharField(max_length=100, null=False)  # Nama file PDF
    url_file = models.CharField(max_length=500, null=False)  # Link Excel di Google Drive
    tgl_terbit = models.DateField(null=False)
    tgl_up = models.DateTimeField(auto_now=True)
    deskripsi_abstrak = models.TextField(blank=True, null=True)
    ukuran_file = models.CharField(max_length=50, blank=True, null=True)
    jumlah_halaman = models.IntegerField(blank=True, null=True)
    id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return self.judul_brs

class BRSsheet(models.Model):
    id_brssheet = models.AutoField(primary_key=True)
    id_brsexcel = models.ForeignKey(BRSExcel, on_delete=models.CASCADE)
    judul_sheet = models.CharField(max_length=250, null=False)
    # nama_tabel_lengkap = models.TextField(blank=True, null=True) # <-- TAMBAHKAN BARIS INI
    nama_tabel_ver2 = models.TextField(blank=True, null=True) # <-- TAMBAHKAN INI
    file_sheet = models.CharField(max_length=500, null=False)  # Link ke sheet di Google Drive
    # deskripsi = models.TextField(blank=True, null=True)  # Field deskripsi yang baru

    def __str__(self):
        return self.judul_sheet
