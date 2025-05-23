from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from orders.utils import Cart
from masterclasses.models import Event
from decimal import Decimal
import json

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def fetch_cart_price(request):
    """Get cart price information"""
    try:
        data = json.loads(request.body)
        product_unit_list = data.get('product_unit_list', [])
        promo_str = data.get('promo', '')
        
        cart = Cart(request)
        if promo_str:
            cart.set_promo_code(promo_str)
        
        # Add items to cart temporarily
        for unit in product_unit_list:
            if unit.startswith('certificate_'):
                amount = unit.split('_')[1]
                cart.add('certificate', amount, 1)  # Always add with quantity 1 for certificates
            else:
                event_id, guests_amount, _ = unit.split('_')
                cart.add('event', event_id, int(guests_amount))
        
        result = {
            'total_amount': float(cart.get_total_amount()),
            'sale': float(cart.get_sale()),
            'promo_sale': float(cart.get_promo_sale()),
            'total_sale': float(cart.get_total_sale()),
            'final_amount': float(cart.get_final_amount())
        }
        
        # Clear temporary cart
        cart.clear()
        
        return Response(result)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def fetch_product_units(request):
    """Get product units information"""
    try:
        data = json.loads(request.body)
        product_unit_list = data.get('product_unit_list', [])
        result = []
        
        for unit in product_unit_list:
            if unit.startswith('certificate_'):
                # Handle certificate
                amount = unit.split('_')[1]
                result.append({
                    'type': 'certificate',
                    'amount': amount
                })
            else:
                # Handle masterclass event
                event_id, guests_amount, _ = unit.split('_')
                event = Event.objects.get(id=event_id)
                masterclass = event.masterclass
                
                # Get address and contacts from nested parameters structure
                params = masterclass.parameters
                address = ''
                contacts = ''
                if isinstance(params, dict) and 'parameters' in params:
                    params_inner = params['parameters']
                    if isinstance(params_inner, dict):
                        address = params_inner.get('Адрес', [''])[0]
                        contacts = params_inner.get('Контакты', [''])[0]

                # Корректная обработка bucket_link
                bucket_links = masterclass.bucket_link
                if isinstance(bucket_links, str):
                    bucket_links = [{'url': bucket_links}]
                elif isinstance(bucket_links, list):
                    if all(isinstance(x, dict) and 'url' in x for x in bucket_links):
                        bucket_links = bucket_links
                    elif all(isinstance(x, str) for x in bucket_links):
                        bucket_links = [{'url': x} for x in bucket_links]
                    else:
                        bucket_links = [{'url': str(x)} for x in bucket_links]
                else:
                    bucket_links = [{'url': str(bucket_links)}]

                result.append({
                    'id': event.id,
                    'name': masterclass.name,
                    'in_wishlist': False,
                    'availability': event.get_remaining_seats() >= int(guests_amount),
                    'bucket_link': bucket_links,
                    'slug': masterclass.slug,
                    'guestsAmount': int(guests_amount),
                    'totalPrice': float(masterclass.final_price * int(guests_amount)),
                    'date': {
                        'id': event.id,
                        'start_datetime': event.start_datetime.isoformat(),
                        'end_datetime': event.end_datetime.isoformat()
                    },
                    'address': address,
                    'contacts': contacts,
                    'type': 'master_class'
                })
        
        return Response(result)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST) 