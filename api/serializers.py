# from rest_framework import serializers
# from .models import RentalCompany,  Vehicle


# class RentalCompanySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = RentalCompany
#         fields = [
#             'id',
#             'name',
#             'address',
#             'phone_number',
#             'email',
#             'portal_url',
#         ]


# # class HotelSerializer(serializers.ModelSerializer):
# #     rental_company = serializers.PrimaryKeyRelatedField(queryset=RentalCompany.objects.all())

# #     class Meta:
# #         model = Hotel
# #         fields = [
# #             'id',
# #             'name',
# #             'location',
# #             'phone',
# #             'email',
# #             'rental_company',
# #             'guest_booking_url',
# #         ]


# class VehicleSerializer(serializers.ModelSerializer):
#     rental_company = serializers.PrimaryKeyRelatedField(queryset=RentalCompany.objects.all())

#     class Meta:
#         model = Vehicle
#         fields = [
#             'id',
#             'vehicle_type',
#             'model',
#             'plate_number',
#             'description',
#             'status',
#             'price_per_hour',
#             'max_price_per_day',
#             'rental_company',
#             'in_car_extension_url',
#         ]
