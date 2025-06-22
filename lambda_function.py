import os
import io
import json
import boto3
from PIL import Image

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1') 

TARGET_BUCKET_NAME = os.environ.get('TARGET_BUCKET_NAME')

s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

def lambda_handler(event, context):

    print(f"Evento recebido: {json.dumps(event, indent=2)}")

    if not TARGET_BUCKET_NAME:
        print("Erro: Variável de ambiente TARGET_BUCKET_NAME não configurada.")
        return {
            'statusCode': 500,
            'body': json.dumps('Erro de configuração: TARGET_BUCKET_NAME não definido.')
        }

    for record in event['Records']:
        bucket_name = record['s3']['bucket']['name']
        object_key = record['s3']['object']['key']

        print(f"Processando arquivo {object_key} do bucket {bucket_name}")

        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            image_content = response['Body'].read()

            image = Image.open(io.BytesIO(image_content))

            original_width, original_height = image.size
            if original_width > 300:
                new_width = 300
                new_height = int((new_width / original_width) * original_height)
                image.thumbnail((new_width, new_height), Image.Resampling.LANCZOS)
                print(f"Imagem redimensionada de {original_width}x{original_height} para {new_width}x{new_height}")
            else:
                print(f"Imagem já é pequena ({original_width}x{original_height}), sem necessidade de redimensionamento.")

            img_byte_arr = io.BytesIO()
            image_format = image.format if image.format else 'JPEG' 
            image.save(img_byte_arr, format=image_format)
            img_byte_arr.seek(0) 

            resized_key = f"resized/{object_key}" 
            
            s3_client.put_object(
                Bucket=TARGET_BUCKET_NAME,
                Key=resized_key,
                Body=img_byte_arr,
                ContentType=f'image/{image_format.lower()}' 
            )
            print(f"Imagem redimensionada salva em s3://{TARGET_BUCKET_NAME}/{resized_key}")

        except Exception as e:
            print(f"Erro ao processar {object_key}: {e}")

    return {
        'statusCode': 200,
        'body': json.dumps('Processamento de imagens concluído.')
    }