from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.panel import Panel
from rich import box
from rich.table import Table
from rich.progress import Progress
import os

class PageSpeedReporter:
    def __init__(self, api_key=None):
        self.api_key = 'API_KEY_HERE' or os.getenv('PAGESPEED_API_KEY')
        self.console = Console()
        
    def analyze_url(self, url, strategy):
        api_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        params = {
            'url': url,
            'key': self.api_key,
            'strategy': strategy
        }
        
        try:
            response = requests.get(api_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            audits = data['lighthouseResult']['audits']
            categories = data['lighthouseResult']['categories']
            
            result = {
                'url': url,
                'strategy': strategy,
                'score': round(categories['performance']['score'] * 100),
                'metrics': {
                    'First Contentful Paint': self._get_metric(audits['first-contentful-paint']),
                    'Speed Index': self._get_metric(audits['speed-index']),
                    'Largest Contentful Paint': self._get_metric(audits['largest-contentful-paint']),
                    'Time to Interactive': self._get_metric(audits['interactive']),
                    'Total Blocking Time': self._get_metric(audits['total-blocking-time']),
                    'Cumulative Layout Shift': self._get_metric(audits['cumulative-layout-shift'])
                },
                'opportunities': self._get_opportunities(audits)
            }
            return result
            
        except Exception as e:
            self.console.print(f"[red]Error analyzing {url} ({strategy}): {str(e)}[/red]")
            return None
            
    def _get_metric(self, audit):
        return {
            'score': audit['score'],
            'value': audit['numericValue'] / 1000 if 'numericValue' in audit else 0,
            'displayValue': audit['displayValue']
        }
        
    def _get_opportunities(self, audits):
        opportunity_keys = [
            'render-blocking-resources',
            'unused-css-rules',
            'unused-javascript',
            'modern-image-formats',
            'offscreen-images'
        ]
        
        opportunities = []
        for key in opportunity_keys:
            if key in audits:
                audit = audits[key]
                opportunities.append({
                    'title': audit['title'],
                    'description': audit['description'],
                    'score': audit['score'],
                    'numericValue': audit.get('numericValue', 0),
                    'displayValue': audit.get('displayValue', '')
                })
        return opportunities

    def get_score_color(self, score):
        if score >= 90:
            return "green"
        elif score >= 50:
            return "yellow"
        return "red"

    def display_metrics(self, metrics):
        table = Table(box=box.SIMPLE)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_column("Score", justify="right")

        for metric_name, metric_data in metrics.items():
            score_color = self.get_score_color(metric_data['score'] * 100)
            table.add_row(
                metric_name,
                metric_data['displayValue'],
                f"[{score_color}]{metric_data['score'] * 100:.0f}[/{score_color}]"
            )
        return table

    def display_opportunities(self, opportunities):
        table = Table(box=box.SIMPLE, show_header=False)
        table.add_column("Content", style="cyan", width=100)

        for opp in opportunities:
            if opp['score'] < 1:
                score_color = self.get_score_color(opp['score'] * 100)
                savings = f" • Potential savings: {opp['displayValue']}" if opp['displayValue'] else ""
                table.add_row(
                    f"[{score_color}]● {opp['title']}[/{score_color}]{savings}\n"
                    f"  {opp['description']}"
                )
        return table

    def analyze_urls(self, urls):
        with Progress() as progress:
            task = progress.add_task("[green]Analyzing URLs...", total=len(urls) * 2)
            
            for url in urls:
                desktop_result = self.analyze_url(url, 'desktop')
                progress.update(task, advance=1)
                
                mobile_result = self.analyze_url(url, 'mobile')
                progress.update(task, advance=1)
                
                if desktop_result and mobile_result:
                    self.display_report(url, desktop_result, mobile_result)

    def display_report(self, url, desktop_result, mobile_result):
        self.console.print(f"\n[bold]Performance Report for {url}[/bold]")
        
        for result in [desktop_result, mobile_result]:
            strategy = result['strategy'].title()
            score = result['score']
            score_color = self.get_score_color(score)
            
            self.console.print(f"\n[bold]{strategy} Results[/bold]")
            self.console.print(Panel(
                f"[{score_color}]Performance Score: {score}[/{score_color}]",
                title=f"{strategy} Score"
            ))

            self.console.print(f"\n[bold]{strategy} Lab Data[/bold]")
            self.console.print(self.display_metrics(result['metrics']))

            self.console.print(f"\n[bold]{strategy} Opportunities[/bold]")
            self.console.print(self.display_opportunities(result['opportunities']))

if __name__ == "__main__":
    urls = [
        'https://example.com'
    ]
    
    reporter = PageSpeedReporter()
    reporter.analyze_urls(urls)
