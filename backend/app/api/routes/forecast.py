from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional, List
import pandas as pd
import os
import uuid
from datetime import datetime

from ...schemas.models import (
    ForecastRequest, ForecastResponse, ForecastResult,
    ModelType, DataStatus, UploadedFile
)
from ...services.forecasting import ForecastingService
from ...services.data_processor import DataProcessor

router = APIRouter()
forecast_service = ForecastingService()
data_processor = DataProcessor()

_uploaded_files = {}


@router.post("/upload/{file_type}")
async def upload_file(file_type: str, file: UploadFile = File(...)):
    allowed_types = ['sales', 'media_plan', 'promotions', 'holidays', 'events']
    if file_type not in allowed_types:
        raise HTTPException(400, f"File type must be one of: {allowed_types}")
    
    if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(400, "File must be CSV or Excel format")
    
    file_id = str(uuid.uuid4())
    file_path = os.path.join("uploads", f"{file_id}_{file.filename}")
    
    os.makedirs("uploads", exist_ok=True)
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    try:
        df = data_processor.process_csv(file_path)
        
        if file_type == 'sales':
            validation = data_processor.validate_sales_data(df)
            if not validation['valid']:
                os.remove(file_path)
                raise HTTPException(400, f"Invalid sales data: {validation['errors']}")
        
        uploaded_file = UploadedFile(
            id=file_id,
            filename=file.filename,
            file_type=file_type,
            size=len(content),
            uploaded_at=datetime.now(),
            status=DataStatus.READY
        )
        
        _uploaded_files[file_id] = {
            'path': file_path,
            'type': file_type,
            'data': df,
            'metadata': uploaded_file
        }
        
        return {
            'file_id': file_id,
            'filename': file.filename,
            'type': file_type,
            'size': len(content),
            'row_count': len(df),
            'columns': list(df.columns)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(500, f"Error processing file: {str(e)}")


@router.post("/analyze")
async def analyze_data(file_id: str):
    if file_id not in _uploaded_files:
        raise HTTPException(404, "File not found")
    
    file_data = _uploaded_files[file_id]
    
    if file_data['type'] != 'sales':
        raise HTTPException(400, "Only sales data can be analyzed")
    
    df = file_data['data']
    
    validation = data_processor.validate_sales_data(df)
    
    if not validation['valid']:
        raise HTTPException(400, f"Invalid data: {validation['errors']}")
    
    has_external = any(
        f['type'] in ['media_plan', 'promotions', 'holidays', 'events']
        for f in _uploaded_files.values()
    )
    
    analysis = forecast_service.analyze_data(
        df, 
        validation['date_column'],
        validation['value_column'],
        has_external
    )
    
    return {
        'validation': validation,
        'analysis': analysis
    }


@router.post("/forecast", response_model=ForecastResponse)
async def create_forecast(request: ForecastRequest):
    if not request.models:
        raise HTTPException(400, "At least one model must be selected")
    
    sales_file = None
    for file_id, file_data in _uploaded_files.items():
        if file_data['type'] == 'sales':
            sales_file = file_data
            break
    
    if sales_file is None:
        raise HTTPException(400, "Sales data must be uploaded first")
    
    data = {'sales': sales_file['data']}
    
    for file_id, file_data in _uploaded_files.items():
        if file_data['type'] == 'media_plan' and request.include_media_plan:
            data['media_plan'] = data_processor.process_media_plan(file_data['data'])
        elif file_data['type'] == 'promotions' and request.include_promotions:
            data['promotions'] = data_processor.process_promotions(file_data['data'])
        elif file_data['type'] == 'holidays' and request.include_holidays:
            data['holidays'] = data_processor.process_holidays(file_data['data'])
        elif file_data['type'] == 'events' and request.include_events:
            data['events'] = data_processor.process_events(file_data['data'])
    
    try:
        result = forecast_service.run_forecast(request, data)
        
        return ForecastResponse(
            id=result.forecast_id,
            status=DataStatus.READY,
            message="Forecast completed successfully",
            best_model=result.results.keys().__iter__().__next__() if result.results else None,
            model_rankings=[{'model': k, **v} for k, v in result.results.items()]
        )
        
    except Exception as e:
        raise HTTPException(500, f"Forecast error: {str(e)}")


@router.get("/forecast/{forecast_id}")
async def get_forecast(forecast_id: str):
    result = forecast_service.get_forecast(forecast_id)
    
    if result is None:
        raise HTTPException(404, "Forecast not found")
    
    return {
        'forecast_id': result.forecast_id,
        'name': result.request.name,
        'created_at': result.created_at.isoformat(),
        'request': result.request.dict(),
        'results': {
            model_name: {
                'model_name': mr.model_name,
                'metrics': mr.metrics,
                'forecast_values': mr.forecast_values
            }
            for model_name, mr in result.results.items()
        },
        'ensemble': result.ensemble.dict() if result.ensemble else None
    }


@router.get("/forecasts")
async def list_forecasts():
    return forecast_service.list_forecasts()


@router.delete("/file/{file_id}")
async def delete_file(file_id: str):
    if file_id not in _uploaded_files:
        raise HTTPException(404, "File not found")
    
    file_data = _uploaded_files[file_id]
    if os.path.exists(file_data['path']):
        os.remove(file_data['path'])
    
    del _uploaded_files[file_id]
    
    return {'message': 'File deleted successfully'}
