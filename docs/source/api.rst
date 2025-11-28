API Reference
=============

Users Service
-------------

.. http:post:: /users/register

   Registers a new user. Requires admin role for elevated role assignment.

.. http:post:: /users/login

   Issues a JWT access token via OAuth2 password flow.

Rooms Service
-------------

.. http:post:: /rooms

   Creates a new meeting room (Admin/Facility Manager).

.. http:get:: /rooms

   Returns filtered room inventory with optional capacity, location, and equipment filters.

.. http:get:: /rooms/{room_id}/status

   Returns cached availability status. Include ``force_refresh=true`` to bypass the TTL cache.

Bookings Service
----------------

.. http:post:: /bookings

   Creates a booking, ensuring no overlapping reservations exist.

.. http:get:: /bookings/availability

   Checks availability for a time range and room id.

.. http:get:: /analytics/rooms/popularity

   Returns the most frequently booked rooms with counts (Admin/Facility Manager roles).

.. http:get:: /analytics/users/activity

   Returns user booking leaders with counts (Admin/Facility Manager roles).

Reviews Service
---------------

.. http:post:: /reviews

   Submits a sanitized review for a meeting room.

.. http:post:: /reviews/{id}/flag

   Flags or unflags a review (Moderator/Admin roles).
