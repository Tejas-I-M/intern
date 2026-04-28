"""
Product Affinity Analysis - Identifies products frequently purchased together
Uses association rule mining to find cross-sell opportunities and product bundles
"""

import pandas as pd
import numpy as np
from itertools import combinations
from collections import Counter


class AffinityAnalyzer:
    """Product affinity and market basket analysis"""
    
    def __init__(self):
        self.affinity_matrix = None
        self.rules = None
    
    def analyze_affinity(self, df, product_col=None, transaction_col=None, 
                        amount_col=None, min_support=0.02, min_confidence=0.3):
        """
        Analyze product affinity using market basket analysis
        
        Args:
            df: DataFrame with transaction data
            product_col: Product/Item column name
            transaction_col: Transaction ID column (groups items together)
            amount_col: Optional: Transaction amount column
            min_support: Minimum support threshold (default 0.02 = 2%)
            min_confidence: Minimum confidence threshold (default 0.3 = 30%)
            
        Returns:
            dict with association rules, affinity matrix, and recommendations
        """
        try:
            if df is None or df.empty:
                return {
                    'success': False,
                    'message': 'Empty dataset',
                    'rules': [],
                    'affinity_matrix': {}
                }
            
            df_copy = df.copy()
            
            # Auto-detect columns
            if product_col is None:
                product_candidates = [col for col in df.columns 
                                     if col.lower() in ['product', 'product_name', 'item', 'category', 'productname']]
                product_col = product_candidates[0] if product_candidates else None
            
            if transaction_col is None:
                transaction_candidates = [col for col in df.columns 
                                        if col.lower() in ['transaction', 'transaction_id', 'order', 'order_id', 'customer', 'customer_id']]
                transaction_col = transaction_candidates[0] if transaction_candidates else None
            
            if product_col is None or transaction_col is None:
                return {
                    'success': False,
                    'message': 'Required columns not found (product, transaction_id)',
                    'rules': [],
                    'affinity_matrix': {}
                }
            
            # Create market basket
            market_basket = df_copy.groupby(transaction_col)[product_col].apply(list).reset_index()
            
            if len(market_basket) == 0:
                return {
                    'success': False,
                    'message': 'No transactions found',
                    'rules': [],
                    'affinity_matrix': {}
                }
            
            # Calculate support for individual items
            all_items = []
            for items in market_basket[product_col]:
                all_items.extend(items)
            
            item_support = Counter(all_items)
            total_transactions = len(market_basket)
            item_support_pct = {item: count / total_transactions 
                               for item, count in item_support.items()}
            
            # Filter items by minimum support
            frequent_items = {item: support for item, support in item_support_pct.items() 
                            if support >= min_support}
            
            if len(frequent_items) < 2:
                return {
                    'success': False,
                    'message': f'Not enough frequent items (found {len(frequent_items)}, need at least 2)',
                    'rules': [],
                    'affinity_matrix': {}
                }
            
            # Generate association rules
            rules = []
            affinity_scores = {}
            
            # Find product pairs and calculate metrics
            for transaction_items in market_basket[product_col]:
                # Filter by frequent items
                transaction_items = [item for item in transaction_items 
                                    if item in frequent_items]
                
                # Generate pairs
                if len(transaction_items) >= 2:
                    pairs = list(combinations(sorted(set(transaction_items)), 2))
                    for pair in pairs:
                        pair_key = f"{pair[0]} -> {pair[1]}"
                        affinity_scores[pair_key] = affinity_scores.get(pair_key, 0) + 1
            
            # Calculate confidence and lift for each pair
            for pair_key, pair_count in affinity_scores.items():
                product_a, product_b = pair_key.split(' -> ')
                
                # Support for the pair
                pair_support = pair_count / total_transactions
                
                # Confidence: P(B|A) = Support(A,B) / Support(A)
                confidence = pair_count / item_support[product_a] \
                    if item_support[product_a] > 0 else 0
                
                # Lift: P(A,B) / (P(A) * P(B))
                lift = pair_support / (item_support_pct[product_a] * item_support_pct[product_b]) \
                    if (item_support_pct[product_a] * item_support_pct[product_b]) > 0 else 0
                
                # Filter by minimum confidence
                if confidence >= min_confidence and lift > 1:
                    rules.append({
                        'product_a': product_a,
                        'product_b': product_b,
                        'support': float(pair_support),
                        'confidence': float(confidence),
                        'lift': float(lift),
                        'co_purchase_count': int(pair_count),
                        'strength': 'Very Strong' if lift > 3 else 'Strong' if lift > 2 else 'Moderate'
                    })
            
            # Sort by lift (most important metric)
            rules = sorted(rules, key=lambda x: x['lift'], reverse=True)
            
            # Build affinity matrix
            affinity_matrix = {}
            for product in frequent_items.keys():
                affinity_matrix[product] = {
                    'support': float(frequent_items[product]),
                    'frequency': int(item_support[product]),
                    'related_products': []
                }
            
            # Add related products to matrix
            for rule in rules[:50]:  # Top 50 rules
                product_a = rule['product_a']
                product_b = rule['product_b']
                
                if product_a in affinity_matrix:
                    affinity_matrix[product_a]['related_products'].append({
                        'product': product_b,
                        'confidence': rule['confidence'],
                        'lift': rule['lift']
                    })
            
            # Generate recommendations
            recommendations = []
            for rule in rules[:10]:  # Top 10 rules
                recommendation = {
                    'when_bought': rule['product_a'],
                    'also_recommend': rule['product_b'],
                    'likelihood': f"{rule['confidence']*100:.1f}%",
                    'strength': rule['strength'],
                    'co_purchase_count': rule['co_purchase_count'],
                    'lift_multiplier': f"{rule['lift']:.2f}x",
                    'rationale': self._generate_rationale(rule)
                }
                recommendations.append(recommendation)
            
            # Summary statistics
            summary = {
                'total_products': len(frequent_items),
                'total_rules': len(rules),
                'top_product_pair': f"{rules[0]['product_a']} & {rules[0]['product_b']}" \
                    if rules else 'N/A',
                'highest_confidence': float(max([r['confidence'] for r in rules], default=0)),
                'highest_lift': float(max([r['lift'] for r in rules], default=0)),
                'average_confidence': float(np.mean([r['confidence'] for r in rules])) \
                    if rules else 0,
                'average_lift': float(np.mean([r['lift'] for r in rules])) \
                    if rules else 0,
                'opportunities_count': len([r for r in rules if r['strength'] in ['Strong', 'Very Strong']])
            }
            
            # Insights
            insights = []
            insights.append(f"Found {len(rules)} product associations")
            insights.append(f"Top combo: {summary['top_product_pair']} " +
                          f"({summary['highest_confidence']*100:.0f}% confidence)")
            
            if summary['opportunities_count'] > 0:
                strong_rules = [r for r in rules[:5] if r['strength'] == 'Very Strong']
                if strong_rules:
                    insights.append(f"{len(strong_rules)} very strong associations identified")
            
            insights.append(f"Cross-sell potential: {summary['average_lift']:.1f}x" +
                          f" average lift across rules")
            
            return {
                'success': True,
                'message': 'Product affinity analysis completed',
                'rules': rules[:50],  # Return top 50 rules
                'affinity_matrix': affinity_matrix,
                'recommendations': recommendations,
                'summary': summary,
                'insights': insights
            }
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f'Affinity analysis failed: {str(e)}',
                'rules': [],
                'affinity_matrix': {}
            }
    
    def _generate_rationale(self, rule):
        """Generate business rationale for association rule"""
        if rule['lift'] > 3:
            return f"Extremely likely to purchase {rule['product_b']} when " + \
                   f"buying {rule['product_a']} - strong bundling opportunity"
        elif rule['lift'] > 2:
            return f"Likely to purchase {rule['product_b']} with " + \
                   f"{rule['product_a']} - cross-sell opportunity"
        else:
            return f"Moderate chance of purchasing {rule['product_b']} with " + \
                   f"{rule['product_a']} - upsell potential"


def product_affinity(df, product_col=None, transaction_col=None, 
                    amount_col=None, min_support=0.02, min_confidence=0.3):
    """Quick product affinity analysis function"""
    analyzer = AffinityAnalyzer()
    return analyzer.analyze_affinity(df, product_col, transaction_col, 
                                    amount_col, min_support, min_confidence)
