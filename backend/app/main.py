import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine
import models
from routes import router
from api.health           import router as health_router
from api.predict          import router as predict_router
from api.lessons          import router as lessons_router
from api.sessions         import router as sessions_router
from api.preprocess       import router as preprocess_router
from api.assessment       import router as assessment_router
from api.progress         import router as progress_router
from api.assessment_engine import router as assessment_engine_router
from api.feedback         import router as feedback_router
from api.review           import router as review_router
from api.error_analysis   import router as error_analysis_router
from api.learning_journey import router as learning_journey_router
from api.adaptive_learning import router as adaptive_learning_router
from api.assess_frame     import router as assess_frame_router
from api.learner_state    import router as learner_state_router
from api.reports          import router as reports_router
from api.dashboard        import router as dashboard_router        # ← NEW
from api.certification import router as certification_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sign Language Learning & Assessment Platform",
    description="AI-powered sign language learning platform",
    version="0.3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router,                   prefix="/api")
app.include_router(health_router,            prefix="/api")
app.include_router(predict_router,           prefix="/api")
app.include_router(lessons_router,           prefix="/api")
app.include_router(sessions_router,          prefix="/api")
app.include_router(preprocess_router,        prefix="/api")
app.include_router(assessment_router,        prefix="/api")
app.include_router(progress_router,          prefix="/api")
app.include_router(assessment_engine_router, prefix="/api")
app.include_router(feedback_router,          prefix="/api")
app.include_router(review_router,            prefix="/api")
app.include_router(error_analysis_router,    prefix="/api")
app.include_router(learning_journey_router,  prefix="/api")
app.include_router(adaptive_learning_router, prefix="/api")
app.include_router(assess_frame_router,      prefix="/api")
app.include_router(learner_state_router,     prefix="/api")
app.include_router(reports_router,           prefix="/api")
app.include_router(dashboard_router,         prefix="/api")        # ← NEW
app.include_router(certification_router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Sign Language Platform API is running", "version": "0.3.0"}