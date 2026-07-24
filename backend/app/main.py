from fastapi import FastAPI
from database import engine
import models
from routes import router
from api.health import router as health_router
from api.predict import router as predict_router
from api.lessons import router as lessons_router
from api.sessions import router as sessions_router
from api.preprocess import router as preprocess_router
from api.assessment import router as assessment_router
from api.progress import router as progress_router
from api.assessment_engine import router as assessment_engine_router
from api.feedback import router as feedback_router
from api.review import router as review_router

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sign Language Learning & Assessment Platform",
    description="AI-powered sign language learning platform",
    version="0.1.0"
)

app.include_router(router, prefix="/api")
app.include_router(health_router, prefix="/api")
app.include_router(predict_router, prefix="/api")
app.include_router(lessons_router, prefix="/api")
app.include_router(sessions_router, prefix="/api")
app.include_router(preprocess_router, prefix="/api")
app.include_router(assessment_router, prefix="/api")
app.include_router(progress_router, prefix="/api")
app.include_router(assessment_engine_router, prefix="/api")
app.include_router(feedback_router, prefix="/api")
app.include_router(review_router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Sign Language Platform API is running"}