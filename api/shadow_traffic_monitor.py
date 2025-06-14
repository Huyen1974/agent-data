"""
CLI140g.1: Shadow Traffic Monitoring System
Monitors 1% shadow traffic routing for 24 hours to validate API Gateway stability
"""

import time
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests
from google.cloud import monitoring_v3
from google.cloud import logging as cloud_logging


class ShadowTrafficMonitor:
    """Monitor shadow traffic performance and stability."""
    
    def __init__(self, project_id: str = None):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id")
        self.monitoring_client = monitoring_v3.MetricServiceClient()
        self.logging_client = cloud_logging.Client()
        
        # Set up logging
        self.setup_logging()
        
        # Monitoring configuration
        self.shadow_percentage = 1.0  # 1% shadow traffic
        self.monitoring_duration = 24 * 60 * 60  # 24 hours in seconds
        self.check_interval = 300  # Check every 5 minutes
        self.error_threshold = 5.0  # 5% error rate threshold
        self.latency_threshold = 500  # 500ms latency threshold
        
        # Metrics tracking
        self.metrics = {
            'shadow_requests': 0,
            'shadow_errors': 0,
            'shadow_latency_samples': [],
            'main_requests': 0,
            'main_errors': 0,
            'main_latency_samples': [],
            'start_time': None,
            'last_check': None
        }
        
    def setup_logging(self):
        """Set up logging for shadow traffic monitoring."""
        # Local logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/shadow.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Cloud logging
        self.cloud_handler = self.logging_client.get_default_handler()
        self.cloud_logger = logging.getLogger("shadow-traffic")
        self.cloud_logger.addHandler(self.cloud_handler)
        
    def start_monitoring(self):
        """Start the 24-hour shadow traffic monitoring."""
        self.logger.info("Starting 24-hour shadow traffic monitoring")
        self.metrics['start_time'] = datetime.utcnow()
        
        end_time = self.metrics['start_time'] + timedelta(seconds=self.monitoring_duration)
        
        try:
            while datetime.utcnow() < end_time:
                self.collect_metrics()
                self.analyze_performance()
                self.log_status()
                
                # Sleep until next check
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            self.logger.info("Monitoring interrupted by user")
        except Exception as e:
            self.logger.error(f"Monitoring error: {e}")
        finally:
            self.generate_final_report()
            
    def collect_metrics(self):
        """Collect metrics from Cloud Monitoring."""
        try:
            # Define time range for metric collection
            now = datetime.utcnow()
            start_time = now - timedelta(seconds=self.check_interval)
            
            # Collect shadow traffic metrics
            shadow_metrics = self.get_shadow_metrics(start_time, now)
            main_metrics = self.get_main_metrics(start_time, now)
            
            # Update tracking metrics
            self.update_metrics(shadow_metrics, main_metrics)
            self.metrics['last_check'] = now
            
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
            
    def get_shadow_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get shadow traffic metrics from Cloud Monitoring."""
        try:
            project_name = f"projects/{self.project_id}"
            interval = monitoring_v3.TimeInterval({
                "end_time": {"seconds": int(end_time.timestamp())},
                "start_time": {"seconds": int(start_time.timestamp())},
            })
            
            # Query shadow traffic request count
            request_filter = (
                'resource.type="api_gateway" AND '
                'metric.type="serviceruntime.googleapis.com/api/request_count" AND '
                'metric.labels.shadow_traffic="true"'
            )
            
            request_results = self.monitoring_client.list_time_series(
                request={
                    "name": project_name,
                    "filter": request_filter,
                    "interval": interval,
                }
            )
            
            # Query shadow traffic latency
            latency_filter = (
                'resource.type="api_gateway" AND '
                'metric.type="serviceruntime.googleapis.com/api/request_latencies" AND '
                'metric.labels.shadow_traffic="true"'
            )
            
            latency_results = self.monitoring_client.list_time_series(
                request={
                    "name": project_name,
                    "filter": latency_filter,
                    "interval": interval,
                }
            )
            
            # Process results
            shadow_requests = 0
            shadow_errors = 0
            shadow_latencies = []
            
            for result in request_results:
                for point in result.points:
                    if point.value.int64_value:
                        shadow_requests += point.value.int64_value
                        # Check if this is an error response
                        if hasattr(result.metric, 'labels') and result.metric.labels.get('response_code', '').startswith('5'):
                            shadow_errors += point.value.int64_value
                            
            for result in latency_results:
                for point in result.points:
                    if point.value.distribution_value:
                        # Extract P95 latency
                        mean_latency = point.value.distribution_value.mean
                        shadow_latencies.append(mean_latency * 1000)  # Convert to ms
            
            return {
                'requests': shadow_requests,
                'errors': shadow_errors,
                'latencies': shadow_latencies
            }
            
        except Exception as e:
            self.logger.error(f"Error getting shadow metrics: {e}")
            return {'requests': 0, 'errors': 0, 'latencies': []}
            
    def get_main_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get main traffic metrics from Cloud Monitoring."""
        try:
            project_name = f"projects/{self.project_id}"
            interval = monitoring_v3.TimeInterval({
                "end_time": {"seconds": int(end_time.timestamp())},
                "start_time": {"seconds": int(start_time.timestamp())},
            })
            
            # Query main traffic request count
            request_filter = (
                'resource.type="api_gateway" AND '
                'metric.type="serviceruntime.googleapis.com/api/request_count" AND '
                '(NOT metric.labels.shadow_traffic="true" OR NOT has(metric.labels.shadow_traffic))'
            )
            
            request_results = self.monitoring_client.list_time_series(
                request={
                    "name": project_name,
                    "filter": request_filter,
                    "interval": interval,
                }
            )
            
            # Process results (similar to shadow metrics)
            main_requests = 0
            main_errors = 0
            main_latencies = []
            
            for result in request_results:
                for point in result.points:
                    if point.value.int64_value:
                        main_requests += point.value.int64_value
                        if hasattr(result.metric, 'labels') and result.metric.labels.get('response_code', '').startswith('5'):
                            main_errors += point.value.int64_value
            
            return {
                'requests': main_requests,
                'errors': main_errors,
                'latencies': main_latencies
            }
            
        except Exception as e:
            self.logger.error(f"Error getting main metrics: {e}")
            return {'requests': 0, 'errors': 0, 'latencies': []}
            
    def update_metrics(self, shadow_metrics: Dict[str, Any], main_metrics: Dict[str, Any]):
        """Update tracking metrics with new data."""
        self.metrics['shadow_requests'] += shadow_metrics['requests']
        self.metrics['shadow_errors'] += shadow_metrics['errors']
        self.metrics['shadow_latency_samples'].extend(shadow_metrics['latencies'])
        
        self.metrics['main_requests'] += main_metrics['requests']
        self.metrics['main_errors'] += main_metrics['errors']
        self.metrics['main_latency_samples'].extend(main_metrics['latencies'])
        
    def analyze_performance(self):
        """Analyze shadow traffic performance against thresholds."""
        try:
            # Calculate error rates
            shadow_error_rate = 0
            if self.metrics['shadow_requests'] > 0:
                shadow_error_rate = (self.metrics['shadow_errors'] / self.metrics['shadow_requests']) * 100
            
            main_error_rate = 0
            if self.metrics['main_requests'] > 0:
                main_error_rate = (self.metrics['main_errors'] / self.metrics['main_requests']) * 100
            
            # Calculate latency percentiles
            shadow_p95_latency = 0
            if self.metrics['shadow_latency_samples']:
                shadow_p95_latency = self.calculate_percentile(self.metrics['shadow_latency_samples'], 95)
            
            main_p95_latency = 0
            if self.metrics['main_latency_samples']:
                main_p95_latency = self.calculate_percentile(self.metrics['main_latency_samples'], 95)
            
            # Check thresholds and alert if needed
            if shadow_error_rate > self.error_threshold:
                self.alert_high_error_rate(shadow_error_rate)
                
            if shadow_p95_latency > self.latency_threshold:
                self.alert_high_latency(shadow_p95_latency)
                
            # Log performance comparison
            self.logger.info(f"Performance comparison - Shadow: {shadow_error_rate:.2f}% errors, "
                           f"{shadow_p95_latency:.2f}ms P95 | Main: {main_error_rate:.2f}% errors, "
                           f"{main_p95_latency:.2f}ms P95")
            
        except Exception as e:
            self.logger.error(f"Error analyzing performance: {e}")
            
    def calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile from list of values."""
        if not values:
            return 0
        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]
        
    def alert_high_error_rate(self, error_rate: float):
        """Send alert for high error rate in shadow traffic."""
        message = f"ALERT: Shadow traffic error rate {error_rate:.2f}% exceeds threshold {self.error_threshold}%"
        self.logger.warning(message)
        self.cloud_logger.warning(message)
        
    def alert_high_latency(self, latency: float):
        """Send alert for high latency in shadow traffic."""
        message = f"ALERT: Shadow traffic P95 latency {latency:.2f}ms exceeds threshold {self.latency_threshold}ms"
        self.logger.warning(message)
        self.cloud_logger.warning(message)
        
    def log_status(self):
        """Log current monitoring status."""
        elapsed = datetime.utcnow() - self.metrics['start_time']
        remaining = timedelta(seconds=self.monitoring_duration) - elapsed
        
        # Calculate traffic distribution
        total_requests = self.metrics['shadow_requests'] + self.metrics['main_requests']
        shadow_percentage = 0
        if total_requests > 0:
            shadow_percentage = (self.metrics['shadow_requests'] / total_requests) * 100
        
        status_message = (
            f"Shadow traffic monitoring - Elapsed: {elapsed}, Remaining: {remaining} | "
            f"Shadow: {self.metrics['shadow_requests']} requests ({shadow_percentage:.1f}%), "
            f"{self.metrics['shadow_errors']} errors | "
            f"Main: {self.metrics['main_requests']} requests, {self.metrics['main_errors']} errors"
        )
        
        self.logger.info(status_message)
        
        # Log to Cloud Logging for monitoring dashboard
        self.cloud_logger.info(status_message, extra={
            'shadow_requests': self.metrics['shadow_requests'],
            'shadow_errors': self.metrics['shadow_errors'],
            'main_requests': self.metrics['main_requests'],
            'main_errors': self.metrics['main_errors'],
            'shadow_percentage': shadow_percentage,
            'elapsed_hours': elapsed.total_seconds() / 3600
        })
        
    def generate_final_report(self):
        """Generate final monitoring report."""
        try:
            total_duration = datetime.utcnow() - self.metrics['start_time']
            
            # Calculate final statistics
            total_requests = self.metrics['shadow_requests'] + self.metrics['main_requests']
            shadow_percentage = 0
            shadow_error_rate = 0
            main_error_rate = 0
            
            if total_requests > 0:
                shadow_percentage = (self.metrics['shadow_requests'] / total_requests) * 100
                
            if self.metrics['shadow_requests'] > 0:
                shadow_error_rate = (self.metrics['shadow_errors'] / self.metrics['shadow_requests']) * 100
                
            if self.metrics['main_requests'] > 0:
                main_error_rate = (self.metrics['main_errors'] / self.metrics['main_requests']) * 100
            
            # Calculate latency statistics
            shadow_p50 = self.calculate_percentile(self.metrics['shadow_latency_samples'], 50)
            shadow_p95 = self.calculate_percentile(self.metrics['shadow_latency_samples'], 95)
            main_p50 = self.calculate_percentile(self.metrics['main_latency_samples'], 50)
            main_p95 = self.calculate_percentile(self.metrics['main_latency_samples'], 95)
            
            # Assessment
            assessment = "PASS"
            issues = []
            
            if shadow_error_rate > self.error_threshold:
                assessment = "FAIL"
                issues.append(f"High error rate: {shadow_error_rate:.2f}% > {self.error_threshold}%")
                
            if shadow_p95 > self.latency_threshold:
                assessment = "FAIL"
                issues.append(f"High latency: {shadow_p95:.2f}ms > {self.latency_threshold}ms")
                
            if abs(shadow_percentage - self.shadow_percentage) > 0.5:
                assessment = "WARN"
                issues.append(f"Traffic distribution: {shadow_percentage:.2f}% vs target {self.shadow_percentage}%")
            
            # Generate report
            report = {
                'timestamp': datetime.utcnow().isoformat(),
                'duration_hours': total_duration.total_seconds() / 3600,
                'assessment': assessment,
                'issues': issues,
                'traffic_distribution': {
                    'shadow_percentage': shadow_percentage,
                    'target_percentage': self.shadow_percentage,
                    'total_requests': total_requests
                },
                'shadow_traffic': {
                    'requests': self.metrics['shadow_requests'],
                    'errors': self.metrics['shadow_errors'],
                    'error_rate_percent': shadow_error_rate,
                    'latency_p50_ms': shadow_p50,
                    'latency_p95_ms': shadow_p95
                },
                'main_traffic': {
                    'requests': self.metrics['main_requests'],
                    'errors': self.metrics['main_errors'],
                    'error_rate_percent': main_error_rate,
                    'latency_p50_ms': main_p50,
                    'latency_p95_ms': main_p95
                },
                'thresholds': {
                    'error_rate_percent': self.error_threshold,
                    'latency_ms': self.latency_threshold
                }
            }
            
            # Save report
            report_path = f"logs/shadow_traffic_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            # Log final results
            self.logger.info(f"Shadow traffic monitoring completed - Assessment: {assessment}")
            self.logger.info(f"Final report saved to: {report_path}")
            
            if assessment == "PASS":
                self.logger.info("✅ Shadow traffic validation successful - Ready for production deployment")
            elif assessment == "WARN":
                self.logger.warning("⚠️ Shadow traffic validation completed with warnings")
            else:
                self.logger.error("❌ Shadow traffic validation failed - Issues detected")
            
            for issue in issues:
                self.logger.warning(f"Issue: {issue}")
                
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating final report: {e}")
            return None


def main():
    """Main function to start shadow traffic monitoring."""
    monitor = ShadowTrafficMonitor()
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    print("Starting CLI140g.1 Shadow Traffic Monitoring")
    print("Duration: 24 hours")
    print("Shadow traffic: 1%")
    print("Error threshold: 5%")
    print("Latency threshold: 500ms")
    print("Press Ctrl+C to stop monitoring early")
    print("-" * 50)
    
    monitor.start_monitoring()


if __name__ == "__main__":
    main() 