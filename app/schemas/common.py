from pydantic import BaseModel


class EvaluationResult(BaseModel):
    created_notifications: int
