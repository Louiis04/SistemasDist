import tkinter as tk
from tkinter import filedialog, messagebox
import boto3
import os
from dotenv import load_dotenv 

load_dotenv()

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
SOURCE_BUCKET_NAME = os.environ.get('SOURCE_BUCKET_NAME') 

s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

class ImageUploaderApp:
    def __init__(self, master):
        self.master = master
        master.title("Uploader de Imagens para AWS Lambda")

        self.filepath = None

        self.label_file = tk.Label(master, text="Nenhuma imagem selecionada.")
        self.label_file.pack(pady=10)

        self.btn_select = tk.Button(master, text="Selecionar Imagem", command=self.select_image)
        self.btn_select.pack(pady=5)

        self.btn_upload = tk.Button(master, text="Enviar para Processamento", command=self.upload_image, state=tk.DISABLED)
        self.btn_upload.pack(pady=5)

        self.status_label = tk.Label(master, text="")
        self.status_label.pack(pady=10)

        if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, SOURCE_BUCKET_NAME]):
            messagebox.showerror("Erro de Configuração", "Por favor, configure AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION e SOURCE_BUCKET_NAME no seu arquivo .env ou variáveis de ambiente.")
            self.btn_select.config(state=tk.DISABLED)
            self.status_label.config(text="Erro: Configuração AWS ausente.")


    def select_image(self):
        f_types = [('Imagens', '*.jpg *.jpeg *.png')]
        self.filepath = filedialog.askopenfilename(filetypes=f_types)
        if self.filepath:
            self.label_file.config(text=f"Arquivo selecionado: {os.path.basename(self.filepath)}")
            self.btn_upload.config(state=tk.NORMAL)
            self.status_label.config(text="")
        else:
            self.label_file.config(text="Nenhuma imagem selecionada.")
            self.btn_upload.config(state=tk.DISABLED)

    def upload_image(self):
        if not self.filepath:
            messagebox.showwarning("Nenhuma Imagem", "Por favor, selecione uma imagem primeiro.")
            return

        try:
            filename = os.path.basename(self.filepath)
            self.status_label.config(text=f"Enviando {filename} para S3...")
            self.master.update_idletasks() # Atualiza a GUI imediatamente

            s3_client.upload_file(self.filepath, SOURCE_BUCKET_NAME, filename)
            
            messagebox.showinfo("Sucesso", f"Imagem {filename} enviada para {SOURCE_BUCKET_NAME}!\nO Lambda irá processá-la.")
            self.status_label.config(text=f"{filename} enviado! Processando no Lambda...")
            self.btn_upload.config(state=tk.DISABLED) # Desabilita até nova seleção
            self.label_file.config(text="Nenhuma imagem selecionada.")

        except Exception as e:
            messagebox.showerror("Erro de Upload", f"Ocorreu um erro ao enviar a imagem: {e}")
            self.status_label.config(text=f"Falha no envio: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageUploaderApp(root)
    root.mainloop()