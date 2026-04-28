#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive Chatbot Client for Nexus AI Flask Backend
Demonstrates asking both predefined and custom questions
"""

import requests
import json
import sys
import io
from datetime import datetime
from pathlib import Path
from requests.exceptions import ConnectionError as RequestsConnectionError, RequestException

# Enable UTF-8 output on Windows
if sys.platform == 'win32':
    import codecs
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class ChatbotClient:
    """Client to interact with Nexus AI chatbot"""
    
    def __init__(self, base_url="http://localhost:5000/api", csv_path=None):
        self.base_url = base_url
        self.csv_path = csv_path
        self.session = requests.Session()
        self.user_email = None
        self.file_id = None
        self.chat_history = []
        
        # Predefined questions templates
        self.predefined_questions = {
            "1": "Who are my top customers?",
            "2": "What's my revenue trend this month?",
            "3": "Which customers are at risk?",
            "4": "Which product category sells most?",
            "5": "What will my sales be next month?",
            "6": "How can I increase revenue?"
        }
    
    def print_header(self, text):
        """Print a formatted header"""
        print(f"\n{'='*60}")
        print(f"  {text}")
        print(f"{'='*60}\n")
    
    def print_success(self, text):
        """Print success message"""
        print(f"[OK] {text}")
    
    def print_error(self, text):
        """Print error message"""
        print(f"[ERROR] {text}")
    
    def print_info(self, text):
        """Print info message"""
        print(f"[INFO] {text}")
    
    def signup(self, email, firstName, lastName, password):
        """Sign up a new user"""
        try:
            response = self.session.post(
                f"{self.base_url}/auth/signup",
                json={"email": email, "firstName": firstName, "lastName": lastName, "password": password}
            )
            if response.status_code == 201:
                self.user_email = email
                self.print_success(f"Signup successful: {email}")
                return True
            else:
                self.print_error(f"Signup failed: {response.json()}")
                return False
        except Exception as e:
            self.print_error(f"Signup error: {e}")
            return False
    
    def login(self, email, password):
        """Login user"""
        try:
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json={"email": email, "password": password}
            )
            if response.status_code == 200:
                self.user_email = email
                data = response.json()
                user_name = data.get('user', {}).get('firstName', email)
                self.print_success(f"Login successful: {user_name}")
                return True
            else:
                self.print_error(f"Login failed: {response.json()}")
                return False
        except Exception as e:
            self.print_error(f"Login error: {e}")
            return False
    
    def upload_csv(self, csv_path=None):
        """Upload CSV file"""
        path = csv_path or self.csv_path
        
        if not path or not Path(path).exists():
            self.print_error(f"CSV file not found: {path}")
            return False
        
        try:
            with open(path, 'rb') as f:
                files = {'file': f}
                data = {'dataset_name': f'Dataset_{datetime.now().strftime("%Y%m%d_%H%M%S")}'}
                response = self.session.post(
                    f"{self.base_url}/analysis/upload",
                    files=files,
                    data=data
                )
            
            if response.status_code == 201:
                self.file_id = response.json()['file_id']
                info = response.json()
                self.print_success(f"File uploaded: {self.file_id}")
                print(f"  • Rows: {info['row_count']}")
                print(f"  • Columns: {', '.join(info['columns'][:5])}...")

                mode = info.get('mode', 'full_analytics')
                capabilities = info.get('capabilities', {})
                if mode != 'full_analytics' or not capabilities.get('chatbot', False):
                    self.print_info("Dataset needs column alignment. Attempting automatic remap...")
                    remap_result = self.auto_remap_columns()
                    if remap_result.get('success'):
                        self.print_success("Automatic remap applied successfully")
                    else:
                        self.print_info(f"Automatic remap not applied: {remap_result.get('message', 'no confident mapping found')}")
                return True
            else:
                self.print_error(f"Upload failed: {response.json()}")
                return False
        except Exception as e:
            self.print_error(f"Upload error: {e}")
            return False

    def auto_remap_columns(self, min_confidence=0.6):
        """Try automatic column remap using backend mapping suggestions."""
        if not self.file_id:
            return {'success': False, 'message': 'No file uploaded yet'}

        try:
            resp = self.session.get(f"{self.base_url}/analysis/mapping-suggestions/{self.file_id}", timeout=30)
            if resp.status_code != 200:
                return {'success': False, 'message': f"suggestion endpoint failed: {resp.status_code}"}

            payload = resp.json()
            suggestions = payload.get('suggestions', {})

            required_roles = ['Date', 'Total Amount']
            mapping = {}
            used_sources = set()

            for role in required_roles:
                candidates = suggestions.get(role, [])
                chosen = None
                for cand in candidates:
                    source_col = cand.get('column')
                    confidence = float(cand.get('confidence', 0.0))
                    if source_col and confidence >= min_confidence and source_col not in used_sources:
                        chosen = source_col
                        break
                if not chosen:
                    return {'success': False, 'message': f"No confident candidate for '{role}'"}
                mapping[role] = chosen
                used_sources.add(chosen)

            optional_roles = ['Customer ID', 'Product Category', 'Region', 'Country', 'Gender', 'Age']
            for role in optional_roles:
                candidates = suggestions.get(role, [])
                for cand in candidates:
                    source_col = cand.get('column')
                    confidence = float(cand.get('confidence', 0.0))
                    if source_col and confidence >= min_confidence and source_col not in used_sources:
                        mapping[role] = source_col
                        used_sources.add(source_col)
                        break

            remap_resp = self.session.post(
                f"{self.base_url}/analysis/remap/{self.file_id}",
                json={'mapping': mapping},
                timeout=30
            )

            if remap_resp.status_code == 200:
                result = remap_resp.json()
                mapped = result.get('mapped_columns', mapping)
                self.print_info(f"Mapped columns: {mapped}")
                return {'success': True, 'mapped_columns': mapped}

            return {
                'success': False,
                'message': remap_resp.json().get('message', f"remap failed with status {remap_resp.status_code}")
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def run_analysis(self):
        """Run full analysis"""
        if not self.file_id:
            self.print_error("No file uploaded yet")
            return False
        
        try:
            response = self.session.post(
                f"{self.base_url}/analysis/analyze/{self.file_id}"
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', {})
                snapshot = results.get('business_snapshot') or results.get('kpis') or {}
                analysis_mode = data.get('analysis_mode') or results.get('analysis_mode') or 'unknown'
                capabilities = data.get('capabilities', {})
                
                self.print_success("Analysis completed!")
                print(f"  • Analysis Mode: {analysis_mode}")

                total_revenue = snapshot.get('total_revenue')
                average_order_value = snapshot.get('average_order_value')
                unique_customers = snapshot.get('unique_customers')

                if total_revenue is not None:
                    print(f"  • Total Revenue: ${float(total_revenue):,.2f}")
                else:
                    print("  • Total Revenue: N/A (column mapping may be incomplete)")

                if average_order_value is not None:
                    print(f"  • Avg Order Value: ${float(average_order_value):.2f}")
                else:
                    print("  • Avg Order Value: N/A")

                if unique_customers is not None:
                    print(f"  • Unique Customers: {int(unique_customers)}")
                else:
                    print("  • Unique Customers: N/A")

                if analysis_mode != 'full_analytics':
                    enabled_caps = [k for k, v in capabilities.items() if v]
                    if enabled_caps:
                        print(f"  • Enabled Capabilities: {', '.join(enabled_caps[:8])}")
                    else:
                        print("  • Enabled Capabilities: exploratory summary only")
                
                return True
            else:
                self.print_error(f"Analysis failed: {response.json()}")
                return False
        except Exception as e:
            self.print_error(f"Analysis error: {e}")
            return False
    
    def get_predefined_questions(self):
        """Get list of predefined questions"""
        try:
            response = self.session.get(f"{self.base_url}/analysis/predefined-questions")
            
            if response.status_code == 200:
                return response.json()['questions']
            else:
                return []
        except Exception as e:
            self.print_error(f"Error getting questions: {e}")
            return []
    
    def ask_question(self, question, use_gemini=False):
        """Ask a question to the chatbot"""
        if not self.file_id:
            self.print_error("No analysis data available. Upload and analyze a file first.")
            return False
        
        try:
            print(f"\n[PROCESSING] Question being processed...")

            payload = {"question": question, "use_gemini": use_gemini}
            try:
                response = self.session.post(
                    f"{self.base_url}/analysis/chat/{self.file_id}",
                    json=payload,
                    timeout=45
                )
            except RequestsConnectionError as conn_err:
                self.print_info("Connection dropped, retrying once...")
                # Retry once with Gemini disabled to avoid external-model network fragility.
                payload["use_gemini"] = False
                response = self.session.post(
                    f"{self.base_url}/analysis/chat/{self.file_id}",
                    json=payload,
                    timeout=45
                )
            
            if response.status_code == 200:
                data = response.json()
                answer = data['answer']
                confidence = data.get('confidence', 0)
                source = data.get('source', 'unknown')
                
                self.print_success(f"Answer received (confidence: {confidence:.0%}, source: {source})")
                print(f"\n{'─'*60}")
                print(answer)
                print(f"{'─'*60}\n")
                
                # Store in chat history
                self.chat_history.append({
                    'question': question,
                    'answer': answer,
                    'confidence': confidence,
                    'source': source,
                    'timestamp': datetime.now().isoformat()
                })
                
                return True
            else:
                self.print_error(f"Question failed: {response.json()}")
                return False
        except RequestException as e:
            self.print_error(f"Chat request error: {e}")
            return False
        except Exception as e:
            self.print_error(f"Chat error: {e}")
            return False
    
    def show_predefined_options(self):
        """Show predefined question options"""
        print("\n📚 Predefined Questions:")
        for key, question in self.predefined_questions.items():
            print(f"  {key}. {question}")
        print(f"  0. Ask custom question")
        print(f"  X. Exit chat")
    
    def interactive_chat(self):
        """Start interactive chat mode"""
        if not self.file_id:
            self.print_error("No file uploaded. Please upload a CSV first.")
            return
        
        self.print_header("INTERACTIVE CHATBOT")
        self.print_info("Ask questions about your uploaded data. Type 'h' for help.")
        
        while True:
            self.show_predefined_options()
            raw_choice = input("\nSelect an option (0-6, X to exit): ").strip()
            choice = raw_choice.upper()
            
            if choice == 'X':
                print("\n[GOODBYE] Ending chat session...\n")
                break
            elif choice == 'H':
                self.show_help()
            elif choice in self.predefined_questions:
                question = self.predefined_questions[choice]
                self.ask_question(question, use_gemini=False)
            elif choice == '0':
                question = input("\nEnter your custom question: ").strip()
                if question:
                    use_gemini = input("Use Gemini AI for enhanced answer? (Y/n, default=Yes): ").lower() != 'n'
                    self.ask_question(question, use_gemini=use_gemini)
            else:
                if raw_choice:
                    self.print_info("Treating input as a custom question.")
                    use_gemini = input("Use Gemini AI for enhanced answer? (Y/n, default=Yes): ").lower() != 'n'
                    self.ask_question(raw_choice, use_gemini=use_gemini)
                else:
                    self.print_error("Invalid option. Try again.")
    
    def show_help(self):
        """Show help information"""
        print("""
[HELP] Help:

PREDEFINED QUESTIONS (1-6):
  * Quick answers based on your data analysis
  * Instant response, no API needed
  * High confidence answers

CUSTOM QUESTIONS (0):
  * Ask ANY question about your data
  * Powered by Gemini AI by default
  * Intelligent contextual answers
  * Can ask about trends, forecasts, recommendations

GEMINI AI INTEGRATION:
  * Automatically enabled for custom questions
  * Uses Gemini Pro model for intelligent responses
  * Provides contextual, detailed answers
  * Understand complex business questions
  * Generates insights and recommendations

SUPPORTED TOPICS:
  - Revenue & Sales Analysis
  - Product & Category Performance
  - Customer Segmentation & Behavior
  - Churn & Risk Analysis
  - Sales Forecasts & Predictions
  - Business Recommendations
  - Market Trends
  - Any Custom Question

CHAT HISTORY:
  * All Q&As stored in memory
  * Can be exported after session
  * Included in generated reports

EXAMPLE QUESTIONS:
  * "Which products sold most in January?"
  * "What's the revenue trend?"
  * "How can we reduce churn?"
  * "Recommend top actions to increase revenue"
  * "Customer demographics analysis"
        """)
    
    def show_chat_history(self):
        """Display chat history"""
        if not self.chat_history:
            self.print_info("No chat history yet.")
            return
        
        self.print_header("Chat History")
        
        for i, chat in enumerate(self.chat_history, 1):
            print(f"\n{i}. Q: {chat['question']}")
            print(f"   A: {chat['answer'][:150]}..." if len(chat['answer']) > 150 else f"   A: {chat['answer']}")
            print(f"   • Confidence: {chat['confidence']:.0%}")
            print(f"   • Source: {chat['source']}")
    
    def export_chat_history(self, filename="chat_history.json"):
        """Export chat history to JSON"""
        try:
            with open(filename, 'w') as f:
                json.dump(self.chat_history, f, indent=2)
            self.print_success(f"Chat history exported to {filename}")
            return True
        except Exception as e:
            self.print_error(f"Export error: {e}")
            return False


def main():
    """Main interactive session"""
    
    print("\n" + "+"+"="*58 + "+")
    print("|" + " "*58 + "|")
    print("|" + "  NEXUS AI - INTERACTIVE CHATBOT CLIENT".center(58) + "|")
    print("|" + " "*58 + "|")
    print("+"+"="*58 + "+\n")
    
    # Resolve default dataset from repo structure so folder renames do not break startup.
    team5_root = Path(__file__).resolve().parent.parent
    csv_path = str(team5_root / 'data' / 'retail_sales_dataset.csv')
    client = ChatbotClient(csv_path=csv_path)
    
    # Check if Flask is running
    try:
        response = client.session.get(f"{client.base_url.replace('/api', '')}/api/health")
        if response.status_code != 200:
            raise Exception("Backend not healthy")
    except:
        print("[ERROR] Flask backend is not running!")
        print("   Start it with: cd Team5_module/backend && python app.py")
        sys.exit(1)
    
    client.print_success("Flask backend is running!")
    
    # Authentication
    print("\n[STEP 1] Authentication\n")
    
    auth_choice = input("(1) Login or (2) Signup? Enter 1 or 2: ").strip()
    
    email = input("Email: ").strip()
    password = input("Password: ").strip()
    
    if auth_choice == "2":
        firstName = input("First Name: ").strip()
        lastName = input("Last Name: ").strip()
        if not client.signup(email, firstName, lastName, password):
            sys.exit(1)
    else:
        if not client.login(email, password):
            sys.exit(1)
    
    # File Upload
    print("\n[STEP 2] File Upload\n")
    
    custom_csv = input(f"CSV path (press Enter for default): ").strip()
    if custom_csv:
        csv_path = custom_csv
    
    if not client.upload_csv(csv_path):
        sys.exit(1)
    
    # Analysis
    print("\n[STEP 3] Running Analysis\n")
    
    if not client.run_analysis():
        sys.exit(1)
    
    # Chat
    print("\n[STEP 4] Start Chatting\n")
    
    client.interactive_chat()
    
    # Summary
    if client.chat_history:
        print("\n[SUMMARY] SESSION SUMMARY")
        print(f"  • Questions asked: {len(client.chat_history)}")
        print(f"  • Average confidence: {sum(c['confidence'] for c in client.chat_history) / len(client.chat_history):.0%}")
        
        try:
            export = input("\nExport chat history? (y/n): ").lower() == 'y'
        except EOFError:
            export = False
        if export:
            client.export_chat_history()
    
    client.show_chat_history()
    print("\n[END] Session ended. Thank you for using Nexus AI!\n")


if __name__ == "__main__":
    main()
