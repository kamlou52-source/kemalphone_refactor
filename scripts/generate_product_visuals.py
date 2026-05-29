import vertexai
from vertexai.vision_models import ImageGenerationModel

vertexai.init(project="kemalphone_refactor-prod", location="europe-west1")
model = ImageGenerationModel.from_pretrained("imagegeneration@006")

prompt = "iPhone 13 Pro Space Black, studio product photo, white background, 4K"
images = model.generate_images(prompt=prompt, number_of_images=1)
images[0].save(location="static/img/products/iphone13pro.jpg", include_generation_parameters=False)