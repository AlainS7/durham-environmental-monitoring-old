
from pydantic import BaseModel, RootModel
from typing import List, Optional
from datetime import datetime

# --- WU Models ---

class WUMetric(BaseModel):
    tempAvg: Optional[float] = None
    humidityAvg: Optional[float] = None
    # Add other WU metric fields as needed

class WUObservation(BaseModel):
    stationID: str
    obsTimeUtc: datetime
    metric: WUMetric

class WUResponse(BaseModel):
    observations: List[WUObservation]

# --- TSI Models ---

class TSIMeasurementData(BaseModel):
    value: float

class TSIMeasurement(BaseModel):
    type: str
    data: TSIMeasurementData

class TSISensor(BaseModel):
    measurements: List[TSIMeasurement]

class TSIResponseRecord(BaseModel):
    device_id: str
    timestamp: datetime
    sensors: List[TSISensor]

class TSIResponse(RootModel):
    root: List[TSIResponseRecord]
