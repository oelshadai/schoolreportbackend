from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(['POST'])
@permission_classes([AllowAny])
def debug_student_login(request):
    print("LOGIN HIT")
    print(f"Request data: {request.data}")
    print(f"Request method: {request.method}")
    print(f"Content type: {request.content_type}")
    return Response({"status": "ok", "data_received": request.data})