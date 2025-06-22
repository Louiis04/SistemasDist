import tkinter as tk
from tkinter import filedialog, messagebox
import boto3
import os
from dotenv import load_dotenv
from PIL import Image, ImageTk
import io
import threading
import time

load_dotenv()

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
SOURCE_BUCKET_NAME = os.environ.get('SOURCE_BUCKET_NAME')
TARGET_BUCKET_NAME = os.environ.get('TARGET_BUCKET_NAME')

s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

class ImageUploaderApp:
    def __init__(self, master):
        self.master = master
        master.title("Redimensionador de Imagens com AWS Lambda")

        self.filepath = None
        self.resized_image_data = None 

        self.label_file = tk.Label(master, text="Nenhuma imagem selecionada.")
        self.label_file.pack(pady=10)

        self.btn_select = tk.Button(master, text="Selecionar Imagem", command=self.select_image)
        self.btn_select.pack(pady=5)

        self.btn_upload = tk.Button(master, text="Enviar para Processamento", command=self.start_upload_process, state=tk.DISABLED)
        self.btn_upload.pack(pady=5)

        self.status_label = tk.Label(master, text="")
        self.status_label.pack(pady=10)

        self.image_display_label = tk.Label(master)
        self.image_display_label.pack(pady=10)

        self.btn_download = tk.Button(master, text="Baixar Imagem Redimensionada", command=self.download_resized_image, state=tk.DISABLED)
        self.btn_download.pack(pady=5)

        if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, SOURCE_BUCKET_NAME, TARGET_BUCKET_NAME]):
            messagebox.showerror("Erro de Configuração", "Por favor, configure todas as variáveis de ambiente (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, SOURCE_BUCKET_NAME, TARGET_BUCKET_NAME) no seu arquivo .env.")
            self.btn_select.config(state=tk.DISABLED)
            self.status_label.config(text="Erro: Configuração AWS ausente.")


    def select_image(self):
        self.image_display_label.config(image=None)
        self.btn_download.config(state=tk.DISABLED)
        self.resized_image_data = None

        f_types = [('Imagens', '*.jpg *.jpeg *.png')]
        self.filepath = filedialog.askopenfilename(filetypes=f_types)
        if self.filepath:
            self.label_file.config(text=f"Arquivo selecionado: {os.path.basename(self.filepath)}")
            self.btn_upload.config(state=tk.NORMAL)
            self.status_label.config(text="")
        else:
            self.label_file.config(text="Nenhuma imagem selecionada.")
            self.btn_upload.config(state=tk.DISABLED)

    def start_upload_process(self):
        if not self.filepath:
            messagebox.showwarning("Nenhuma Imagem", "Por favor, selecione uma imagem primeiro.")
            return

        self.btn_upload.config(state=tk.DISABLED)
        self.btn_select.config(state=tk.DISABLED)
        self.btn_download.config(state=tk.DISABLED)
        self.image_display_label.config(image=None) 

        filename = os.path.basename(self.filepath)
        self.status_label.config(text=f"Enviando {filename} para S3 e aguardando processamento...")
        self.master.update_idletasks() 

        upload_thread = threading.Thread(target=self._upload_and_wait_for_resized_image, args=(filename,))
        upload_thread.start()

    def _upload_and_wait_for_resized_image(self, filename):
        try:
            s3_client.upload_file(self.filepath, SOURCE_BUCKET_NAME, filename)
            self.status_label.config(text=f"'{filename}' enviado! Aguardando processamento do Lambda...")

            resized_key = f"resized/{filename}" 
            max_attempts = 30 
            attempt = 0
            found = False

            while attempt < max_attempts:
                try:
                    s3_client.head_object(Bucket=TARGET_BUCKET_NAME, Key=resized_key)
                    found = True
                    break 
                except s3_client.exceptions.ClientError as e:
                    if e.response['Error']['Code'] == '404':
                        pass
                    else:
                        raise e
                
                self.master.after(1000, lambda: self.status_label.config(text=f"Aguardando... ({attempt+1}/{max_attempts})"))
                time.sleep(1) 
                attempt += 1

            if found:
                self.status_label.config(text=f"Imagem redimensionada encontrada! Baixando...")
                
                response = s3_client.get_object(Bucket=TARGET_BUCKET_NAME, Key=resized_key)
                self.resized_image_data = response['Body'].read()

                self.master.after(0, self._display_resized_image)
                self.master.after(0, lambda: self.status_label.config(text="Processamento concluído e imagem exibida!"))
                self.master.after(0, lambda: self.btn_download.config(state=tk.NORMAL))

            else:
                self.status_label.config(text="Erro: Imagem redimensionada não encontrada após o tempo limite.")
                messagebox.showerror("Erro", "A imagem redimensionada não foi encontrada no bucket de destino após o tempo limite.")

        except Exception as e:
            messagebox.showerror("Erro no Processamento", f"Ocorreu um erro no ciclo de upload/processamento: {e}")
            self.status_label.config(text=f"Erro: {e}")
        finally:
            self.master.after(0, lambda: self.btn_upload.config(state=tk.NORMAL))
            self.master.after(0, lambda: self.btn_select.config(state=tk.NORMAL))


    def _display_resized_image(self):
        if self.resized_image_data:
            try:
                image = Image.open(io.BytesIO(self.resized_image_data))
                
                width, height = image.size
                if max(width, height) > 300:
                    ratio = 300 / max(width, height)
                    new_width = int(width * ratio)
                    new_height = int(height * ratio)
                    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

                photo = ImageTk.PhotoImage(image)
                self.image_display_label.config(image=photo)
                self.image_display_label.image = photo 
            except Exception as e:
                messagebox.showerror("Erro de Exibição", f"Falha ao exibir imagem redimensionada: {e}")

    def download_resized_image(self):
        if self.resized_image_data:
            save_path = filedialog.asksaveasfilename(defaultextension=".png", 
                                                    filetypes=[("PNG files", "*.png"), 
                                                                ("JPEG files", "*.jpg"), 
                                                                ("All files", "*.*")],
                                                    initialfile=f"resized_{os.path.basename(self.filepath)}")
            if save_path:
                try:
                    with open(save_path, 'wb') as f:
                        f.write(self.resized_image_data)
                    messagebox.showinfo("Sucesso", f"Imagem salva em: {save_path}")
                except Exception as e:
                    messagebox.showerror("Erro ao Salvar", f"Falha ao salvar a imagem: {e}")
        else:
            messagebox.showwarning("Nenhuma Imagem", "Nenhuma imagem redimensionada para baixar.")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageUploaderApp(root)
    root.mainloop()