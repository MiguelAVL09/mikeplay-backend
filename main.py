import os
import shutil
from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import engine, get_db
import models, schemas

# 1. Creamos las tablas de la base de datos
models.Base.metadata.create_all(bind=engine)

# 2. Creamos la carpeta física en tu PC
os.makedirs("uploads", exist_ok=True)

# 3. ¡AQUÍ NACE LA VARIABLE 'app'!
app = FastAPI(
    title="Tienda de Apps API",
    description="Backend para distribución de proyectos .exe y móviles",
    version="1.0.0"
)

# 4. Configuramos los permisos (CORS) para que React pueda hablarle
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. Montamos la carpeta estática (Ahora sí funciona porque 'app' ya existe)
app.mount("/descargas", StaticFiles(directory="uploads"), name="descargas")

@app.get("/")
def root():
    return {"mensaje": "¡Servidor de la Tienda de Apps funcionando al 100%!"}

# --- NUEVO ENDPOINT: Crear Categoría ---
@app.post("/categorias/", response_model=schemas.Categoria)
def crear_categoria(categoria: schemas.CategoriaCreate, db: Session = Depends(get_db)):
    # 1. Verificamos si ya existe una categoría con ese nombre
    db_categoria = db.query(models.Categoria).filter(models.Categoria.nombre == categoria.nombre).first()
    if db_categoria:
        raise HTTPException(status_code=400, detail="La categoría ya existe")
    
    # 2. Creamos la nueva categoría
    nueva_categoria = models.Categoria(nombre=categoria.nombre)
    db.add(nueva_categoria)
    db.commit()
    db.refresh(nueva_categoria)
    
    return nueva_categoria

# --- ENDPOINT: Obtener todas las Categorías ---
@app.get("/categorias/", response_model=list[schemas.Categoria])
def obtener_categorias(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    categorias = db.query(models.Categoria).offset(skip).limit(limit).all()
    return categorias

# --- ENDPOINT: Crear una App ---
@app.post("/apps/", response_model=schemas.App)
def crear_app(app: schemas.AppCreate, db: Session = Depends(get_db)):
    # 1. Validamos que la categoría realmente exista en la base de datos
    categoria_existe = db.query(models.Categoria).filter(models.Categoria.id == app.categoria_id).first()
    if not categoria_existe:
        raise HTTPException(status_code=404, detail=f"No se puede crear la app: La categoría con id {app.categoria_id} no existe.")

    # 2. Si existe, creamos la app normalmente
    nueva_app = models.App(
        titulo=app.titulo,
        descripcion=app.descripcion,
        icono_url=app.icono_url,
        categoria_id=app.categoria_id
    )
    db.add(nueva_app)
    db.commit()
    db.refresh(nueva_app)
    return nueva_app

# --- ENDPOINT: Obtener todas las Apps ---
@app.get("/apps/", response_model=list[schemas.App])
def obtener_apps(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # Gracias a las "relationships" en models.py, esto traerá también 
    # la info de la categoría y las versiones asociadas a cada app
    apps = db.query(models.App).offset(skip).limit(limit).all()
    return apps

# --- ENDPOINT: Agregar una Versión (CON SUBIDA DE ARCHIVO) ---
@app.post("/apps/{app_id}/versiones/", response_model=schemas.Version)
def crear_version(
    app_id: int, 
    numero_version: str = Form(...),
    notas_lanzamiento: str = Form(...),
    peso_archivo: str = Form(...),
    archivo: UploadFile = File(...), # Aquí recibimos el archivo físico
    db: Session = Depends(get_db)
):
    app_existe = db.query(models.App).filter(models.App.id == app_id).first()
    if not app_existe:
        raise HTTPException(status_code=404, detail="La aplicación no existe.")
    
    # 1. Definir dónde vamos a guardar el archivo en tu PC
    file_location = f"uploads/{archivo.filename}"
    
    # 2. Guardar el archivo físicamente en la carpeta 'uploads'
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(archivo.file, file_object)
        
    # 3. Construir la URL automática apuntando a tu propio servidor
    url_local = f"http://127.0.0.1:8000/descargas/{archivo.filename}"

    # 4. Guardar en la base de datos
    nueva_version = models.Version(
        app_id=app_id,
        numero_version=numero_version,
        notas_lanzamiento=notas_lanzamiento,
        url_descarga=url_local, # Guardamos la URL de tu PC
        peso_archivo=peso_archivo
    )
    db.add(nueva_version)
    db.commit()
    db.refresh(nueva_version)
    return nueva_version

# --- ENDPOINT: Obtener una App por su ID ---
@app.get("/apps/{app_id}", response_model=schemas.App)
def obtener_app(app_id: int, db: Session = Depends(get_db)):
    app_db = db.query(models.App).filter(models.App.id == app_id).first()
    if not app_db:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    return app_db