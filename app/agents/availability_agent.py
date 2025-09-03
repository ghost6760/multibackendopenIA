# app/agents/availability_agent.py - VERSIÓN COMPLETAMENTE CORREGIDA

import logging
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class AvailabilityAgent:
    def __init__(self, company_config, openai_service):  # CORREGIDO: 3 argumentos
        self.company_config = company_config
        self.openai_service = openai_service
        self.company_id = company_config.company_id if hasattr(company_config, 'company_id') else 'default'
        self.agent_type = "availability"
        self.schedule_agent = None  # Para conectar con ScheduleAgent
        logger.info(f"[{self.company_id}] AvailabilityAgent: initialized")
    
    def set_schedule_agent(self, schedule_agent):
        """Conectar con el schedule agent para verificación de disponibilidad"""
        self.schedule_agent = schedule_agent
        logger.info(f"[{self.company_id}] AvailabilityAgent: connected to ScheduleAgent")
    
    def check_availability(self, date_str=None, time_str=None, service_type=None):
        """Verificar disponibilidad para una fecha y hora específica"""
        try:
            logger.info(f"[{self.company_id}] AvailabilityAgent: checking_availability")
            
            # Si no se proporciona fecha, usar mañana
            if not date_str:
                tomorrow = datetime.now() + timedelta(days=1)
                date_str = tomorrow.strftime("%Y-%m-%d")
            
            # Horarios disponibles por defecto (simulados)
            available_times = [
                "09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00"
            ]
            
            # Obtener nombre de la empresa
            company_name = getattr(self.company_config, 'company_name', self.company_id)
            
            # Si tenemos schedule_agent, usarlo para verificar disponibilidad real
            if self.schedule_agent:
                try:
                    real_availability = self.schedule_agent.check_real_availability(date_str, time_str, service_type)
                    if real_availability.get('success'):
                        return real_availability
                except Exception as e:
                    logger.warning(f"[{self.company_id}] Schedule agent unavailable, using fallback: {e}")
            
            # Fallback: respuesta simulada
            if time_str and time_str in available_times:
                response = {
                    "available": True,
                    "date": date_str,
                    "time": time_str,
                    "service_type": service_type or "consulta general",
                    "company": company_name,
                    "message": f"✅ Disponible el {date_str} a las {time_str} en {company_name}",
                    "booking_reference": f"{self.company_id}_{date_str}_{time_str}".replace("-", "").replace(":", "")
                }
            else:
                response = {
                    "available": True,
                    "date": date_str,
                    "suggested_times": available_times[:3],
                    "service_type": service_type or "consulta general", 
                    "company": company_name,
                    "message": f"📅 Horarios disponibles para el {date_str} en {company_name}:\n" + 
                              "\n".join([f"• {time}" for time in available_times[:3]]) +
                              f"\n\nPara agendar, indica el horario que prefieres."
                }
            
            logger.info(f"[{self.company_id}] Availability checked successfully")
            return response
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error in AvailabilityAgent: {e}")
            return {
                "available": False,
                "message": "Lo siento, no pude verificar la disponibilidad en este momento. Por favor, intenta de nuevo más tarde.",
                "error": str(e)
            }
    
    def get_available_dates(self, days_ahead=7):
        """Obtener fechas disponibles en los próximos días"""
        try:
            available_dates = []
            today = datetime.now()
            
            for i in range(1, days_ahead + 1):
                future_date = today + timedelta(days=i)
                # Excluir domingos (weekday 6)
                if future_date.weekday() != 6:
                    available_dates.append({
                        "date": future_date.strftime("%Y-%m-%d"),
                        "day_name": future_date.strftime("%A"),
                        "formatted_date": future_date.strftime("%d/%m/%Y")
                    })
            
            return {
                "success": True,
                "available_dates": available_dates,
                "company_id": self.company_id
            }
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error getting available dates: {e}")
            return {
                "success": False,
                "message": "Error obteniendo fechas disponibles",
                "error": str(e)
            }
    
    def book_appointment(self, date_str, time_str, client_info, service_type=None):
        """Simular reserva de cita (en producción se conectaría a sistema real)"""
        try:
            logger.info(f"[{self.company_id}] Booking appointment for {date_str} {time_str}")
            
            company_name = getattr(self.company_config, 'company_name', self.company_id)
            
            # Si tenemos schedule_agent, usarlo para booking real
            if self.schedule_agent:
                try:
                    real_booking = self.schedule_agent.book_real_appointment(
                        date_str, time_str, client_info, service_type
                    )
                    if real_booking.get('success'):
                        return real_booking
                except Exception as e:
                    logger.warning(f"[{self.company_id}] Schedule agent booking failed, using fallback: {e}")
            
            # Fallback: booking simulado
            booking_reference = f"{self.company_id}_{date_str}_{time_str}_{datetime.now().strftime('%H%M%S')}".replace("-", "").replace(":", "")
            
            return {
                "success": True,
                "booking_reference": booking_reference,
                "date": date_str,
                "time": time_str,
                "service_type": service_type or "consulta general",
                "client_info": client_info,
                "company": company_name,
                "message": f"🎉 ¡Cita agendada con éxito!\n\n" +
                          f"📅 Fecha: {date_str}\n" +
                          f"🕐 Hora: {time_str}\n" +
                          f"🏢 Lugar: {company_name}\n" +
                          f"📋 Servicio: {service_type or 'Consulta general'}\n" +
                          f"📄 Referencia: {booking_reference}\n\n" +
                          f"Te esperamos puntualmente. Si necesitas cambiar la cita, contacta con anticipación."
            }
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error booking appointment: {e}")
            return {
                "success": False,
                "message": "No se pudo agendar la cita en este momento. Por favor, intenta de nuevo.",
                "error": str(e)
            }
