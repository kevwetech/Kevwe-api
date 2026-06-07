from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from .models import (
    SiteSettings,
    HomePage,
    AboutPage,
    Service,
    ContactInfo,
    ContactMessage,
    FAQ,
    Testimonial,
    TeamMember,
    Feature,
    Gallery,
)
from .serializers import (
    SiteSettingsSerializer,
    HomePageSerializer,
    AboutPageSerializer,
    ServiceSerializer,
    ContactInfoSerializer,
    ContactMessageSerializer,
    FAQSerializer,
    TestimonialSerializer,
    TeamMemberSerializer,
    FeatureSerializer,
    GallerySerializer,
)


class SiteSettingsView(APIView):
    """Get and update site settings"""
    permission_classes = []

    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [IsAdmin()]
        return []

    def get(self, request):
        settings = SiteSettings.get_settings()
        serializer = SiteSettingsSerializer(settings)
        return api_response(
            'success',
            'Site settings retrieved successfully',
            data=serializer.data
        )

    def patch(self, request):
        settings = SiteSettings.get_settings()
        serializer = SiteSettingsSerializer(
            settings,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Site settings updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class HomePageView(APIView):
    """Get and update homepage content"""
    permission_classes = []

    def get_permissions(self):
        if self.request.method in ['POST', 'PATCH']:
            return [IsAdmin()]
        return []

    def get(self, request):
        homepage = HomePage.objects.filter(
            is_active=True
        ).first()
        if not homepage:
            return api_response(
                'error',
                'Homepage content not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = HomePageSerializer(homepage)
        return api_response(
            'success',
            'Homepage content retrieved successfully',
            data=serializer.data
        )

    def post(self, request):
        serializer = HomePageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Homepage created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def patch(self, request):
        homepage = HomePage.objects.filter(
            is_active=True
        ).first()
        if not homepage:
            return api_response(
                'error',
                'Homepage not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = HomePageSerializer(
            homepage,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Homepage updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class AboutPageView(APIView):
    """Get and update about page content"""
    permission_classes = []

    def get_permissions(self):
        if self.request.method in ['POST', 'PATCH']:
            return [IsAdmin()]
        return []

    def get(self, request):
        about = AboutPage.objects.filter(
            is_active=True
        ).first()
        if not about:
            return api_response(
                'error',
                'About page not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = AboutPageSerializer(about)
        return api_response(
            'success',
            'About page retrieved successfully',
            data=serializer.data
        )

    def post(self, request):
        serializer = AboutPageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'About page created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def patch(self, request):
        about = AboutPage.objects.filter(
            is_active=True
        ).first()
        if not about:
            return api_response(
                'error',
                'About page not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = AboutPageSerializer(
            about,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'About page updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class ServiceListCreateView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return []

    def get(self, request):
        services = Service.objects.filter(is_active=True)
        featured = request.query_params.get('featured')
        if featured:
            services = services.filter(is_featured=True)
        serializer = ServiceSerializer(services, many=True)
        return api_response(
            'success',
            'Services retrieved successfully',
            data={
                'count': services.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = ServiceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Service created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class ServiceDetailView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE']:
            return [IsAdmin()]
        return []

    def get_object(self, pk):
        try:
            return Service.objects.get(pk=pk)
        except Service.DoesNotExist:
            return None

    def get(self, request, pk):
        service = self.get_object(pk)
        if not service:
            return api_response(
                'error',
                'Service not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = ServiceSerializer(service)
        return api_response(
            'success',
            'Service retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        service = self.get_object(pk)
        if not service:
            return api_response(
                'error',
                'Service not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = ServiceSerializer(
            service,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Service updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        service = self.get_object(pk)
        if not service:
            return api_response(
                'error',
                'Service not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        service.is_active = False
        service.save()
        return api_response(
            'success',
            'Service deleted successfully'
        )


class ContactInfoView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method in ['POST', 'PATCH']:
            return [IsAdmin()]
        return []

    def get(self, request):
        contact = ContactInfo.objects.filter(
            is_active=True
        ).first()
        if not contact:
            return api_response(
                'error',
                'Contact info not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = ContactInfoSerializer(contact)
        return api_response(
            'success',
            'Contact info retrieved successfully',
            data=serializer.data
        )

    def post(self, request):
        serializer = ContactInfoSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Contact info created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def patch(self, request):
        contact = ContactInfo.objects.filter(
            is_active=True
        ).first()
        if not contact:
            return api_response(
                'error',
                'Contact info not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = ContactInfoSerializer(
            contact,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Contact info updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class ContactMessageListView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAdmin()]
        return []

    def get(self, request):
        messages = ContactMessage.objects.all()
        msg_status = request.query_params.get('status')
        if msg_status:
            messages = messages.filter(status=msg_status)
        serializer = ContactMessageSerializer(messages, many=True)
        return api_response(
            'success',
            'Messages retrieved successfully',
            data={
                'count': messages.count(),
                'new': messages.filter(status='new').count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        """Public - send contact message"""
        serializer = ContactMessageSerializer(data=request.data)
        if serializer.is_valid():
            message = serializer.save()

            # Notify admin
            try:
                from apps.notifications.utils import send_notification
                from django.contrib.auth import get_user_model
                User = get_user_model()
                admins = User.objects.filter(role='admin')
                for admin in admins:
                    send_notification(
                        user=admin,
                        title='New Contact Message',
                        message=f'New message from {message.name}: {message.subject}',
                        notification_type='system'
                    )
            except Exception:
                pass

            return api_response(
                'success',
                'Message sent successfully! We will get back to you soon.',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Failed to send message',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class ContactMessageDetailView(APIView):
    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return ContactMessage.objects.get(pk=pk)
        except ContactMessage.DoesNotExist:
            return None

    def get(self, request, pk):
        message = self.get_object(pk)
        if not message:
            return api_response(
                'error',
                'Message not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        # Mark as read
        if message.status == 'new':
            message.status = 'read'
            message.save()
        serializer = ContactMessageSerializer(message)
        return api_response(
            'success',
            'Message retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        """Reply to message"""
        message = self.get_object(pk)
        if not message:
            return api_response(
                'error',
                'Message not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        reply = request.data.get('reply')
        if reply:
            message.reply = reply
            message.status = 'replied'
            message.replied_by = request.user
            message.replied_at = timezone.now()
            message.save()

            # Send reply email
            try:
                from apps.common.email import send_email
                send_email(
                    to_email=message.email,
                    subject=f'Re: {message.subject}',
                    html_content=f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <h2>Hi {message.name}!</h2>
                        <p>Thank you for contacting us. Here is our response to your inquiry:</p>
                        <div style="background: #f9f9f9; padding: 20px; border-radius: 8px;">
                            {reply}
                        </div>
                        <p>If you have any further questions, please don't hesitate to contact us.</p>
                    </div>
                    """
                )
            except Exception:
                pass

        serializer = ContactMessageSerializer(message)
        return api_response(
            'success',
            'Message updated successfully',
            data=serializer.data
        )


class FAQListCreateView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return []

    def get(self, request):
        faqs = FAQ.objects.filter(is_active=True)
        category = request.query_params.get('category')
        featured = request.query_params.get('featured')
        if category:
            faqs = faqs.filter(category=category)
        if featured:
            faqs = faqs.filter(is_featured=True)

        # Group by category
        grouped = {}
        for faq in faqs:
            cat = faq.get_category_display()
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(FAQSerializer(faq).data)

        serializer = FAQSerializer(faqs, many=True)
        return api_response(
            'success',
            'FAQs retrieved successfully',
            data={
                'count': faqs.count(),
                'grouped': grouped,
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = FAQSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'FAQ created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class FAQDetailView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE']:
            return [IsAdmin()]
        return []

    def get_object(self, pk):
        try:
            return FAQ.objects.get(pk=pk)
        except FAQ.DoesNotExist:
            return None

    def get(self, request, pk):
        faq = self.get_object(pk)
        if not faq:
            return api_response(
                'error',
                'FAQ not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        # Increment views
        faq.views += 1
        faq.save()
        serializer = FAQSerializer(faq)
        return api_response(
            'success',
            'FAQ retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        faq = self.get_object(pk)
        if not faq:
            return api_response(
                'error',
                'FAQ not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = FAQSerializer(
            faq,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'FAQ updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        faq = self.get_object(pk)
        if not faq:
            return api_response(
                'error',
                'FAQ not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        faq.is_active = False
        faq.save()
        return api_response(
            'success',
            'FAQ deleted successfully'
        )


class TestimonialListCreateView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return []

    def get(self, request):
        testimonials = Testimonial.objects.filter(
            status='approved',
            is_active=True if hasattr(Testimonial, 'is_active') else True
        )
        featured = request.query_params.get('featured')
        if featured:
            testimonials = testimonials.filter(is_featured=True)
        serializer = TestimonialSerializer(
            testimonials,
            many=True
        )
        return api_response(
            'success',
            'Testimonials retrieved successfully',
            data={
                'count': testimonials.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = TestimonialSerializer(data=request.data)
        if serializer.is_valid():
            testimonial = serializer.save(
                user=request.user,
                status='pending'
            )
            return api_response(
                'success',
                'Testimonial submitted successfully! It will be reviewed before publishing.',
                data=TestimonialSerializer(testimonial).data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Submission failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class TestimonialDetailView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE']:
            return [IsAdmin()]
        return []

    def get_object(self, pk):
        try:
            return Testimonial.objects.get(pk=pk)
        except Testimonial.DoesNotExist:
            return None

    def get(self, request, pk):
        testimonial = self.get_object(pk)
        if not testimonial:
            return api_response(
                'error',
                'Testimonial not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = TestimonialSerializer(testimonial)
        return api_response(
            'success',
            'Testimonial retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        testimonial = self.get_object(pk)
        if not testimonial:
            return api_response(
                'error',
                'Testimonial not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = TestimonialSerializer(
            testimonial,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Testimonial updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        testimonial = self.get_object(pk)
        if not testimonial:
            return api_response(
                'error',
                'Testimonial not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        testimonial.delete()
        return api_response(
            'success',
            'Testimonial deleted successfully'
        )


class TeamMemberListCreateView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return []

    def get(self, request):
        members = TeamMember.objects.filter(is_active=True)
        serializer = TeamMemberSerializer(members, many=True)
        return api_response(
            'success',
            'Team members retrieved successfully',
            data={
                'count': members.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = TeamMemberSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Team member added successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class TeamMemberDetailView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE']:
            return [IsAdmin()]
        return []

    def get_object(self, pk):
        try:
            return TeamMember.objects.get(pk=pk)
        except TeamMember.DoesNotExist:
            return None

    def get(self, request, pk):
        member = self.get_object(pk)
        if not member:
            return api_response(
                'error',
                'Team member not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = TeamMemberSerializer(member)
        return api_response(
            'success',
            'Team member retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        member = self.get_object(pk)
        if not member:
            return api_response(
                'error',
                'Team member not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = TeamMemberSerializer(
            member,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Team member updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        member = self.get_object(pk)
        if not member:
            return api_response(
                'error',
                'Team member not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        member.is_active = False
        member.save()
        return api_response(
            'success',
            'Team member removed successfully'
        )


class FeatureListCreateView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return []

    def get(self, request):
        features = Feature.objects.filter(is_active=True)
        serializer = FeatureSerializer(features, many=True)
        return api_response(
            'success',
            'Features retrieved successfully',
            data={
                'count': features.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = FeatureSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Feature created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class GalleryListCreateView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return []

    def get(self, request):
        gallery = Gallery.objects.filter(is_active=True)
        gallery_type = request.query_params.get('type')
        if gallery_type:
            gallery = gallery.filter(gallery_type=gallery_type)
        serializer = GallerySerializer(gallery, many=True)
        return api_response(
            'success',
            'Gallery retrieved successfully',
            data={
                'count': gallery.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = GallerySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Image added to gallery successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class FullSiteView(APIView):
    """
    Get all site content in one request
    Perfect for frontend to load everything at once
    """
    permission_classes = []

    def get(self, request):
        settings = SiteSettings.get_settings()
        homepage = HomePage.objects.filter(is_active=True).first()
        about = AboutPage.objects.filter(is_active=True).first()
        contact = ContactInfo.objects.filter(is_active=True).first()
        services = Service.objects.filter(is_active=True)
        faqs = FAQ.objects.filter(is_active=True, is_featured=True)
        testimonials = Testimonial.objects.filter(
            status='approved',
            is_featured=True
        )
        team = TeamMember.objects.filter(is_active=True)
        features = Feature.objects.filter(is_active=True)

        return api_response(
            'success',
            'Site content retrieved successfully',
            data={
                'settings': SiteSettingsSerializer(settings).data,
                'homepage': HomePageSerializer(homepage).data if homepage else None,
                'about': AboutPageSerializer(about).data if about else None,
                'contact': ContactInfoSerializer(contact).data if contact else None,
                'services': ServiceSerializer(services, many=True).data,
                'faqs': FAQSerializer(faqs, many=True).data,
                'testimonials': TestimonialSerializer(testimonials, many=True).data,
                'team': TeamMemberSerializer(team, many=True).data,
                'features': FeatureSerializer(features, many=True).data,
            }
        )