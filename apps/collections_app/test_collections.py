import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient

from apps.collections_app.models import Collection


@pytest.fixture
def user(db):
    return User.objects.create_user(username="alice", password="pass1234")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="bob", password="pass1234")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def other_client(other_user):
    client = APIClient()
    client.force_authenticate(user=other_user)
    return client


@pytest.mark.django_db
class TestCollectionAPI:
    url = reverse("collection-list")

    def test_list_requires_auth(self):
        client = APIClient()
        res = client.get(self.url)
        assert res.status_code == 401

    def test_list_empty(self, auth_client):
        res = auth_client.get(self.url)
        assert res.status_code == 200
        assert res.data["results"] == []

    def test_create(self, auth_client, user):
        res = auth_client.post(self.url, {"name": "My Collection"}, format="json")
        assert res.status_code == 201, res.data
        assert res.data["name"] == "My Collection"
        assert res.data["owner"] == user.id
        assert Collection.objects.filter(owner=user, name="My Collection").exists()

    def test_create_sets_owner(self, auth_client, user, other_user):
        res = auth_client.post(
            self.url, {"name": "X", "owner": other_user.id}, format="json"
        )
        assert res.status_code == 201
        assert res.data["owner"] == user.id

    def test_unique_name_per_owner(self, auth_client):
        auth_client.post(self.url, {"name": "Dup"}, format="json")
        res = auth_client.post(self.url, {"name": "Dup"}, format="json")
        assert res.status_code == 400
        assert "name" in res.data

    def test_same_name_different_owners(self, auth_client, other_client):
        auth_client.post(self.url, {"name": "Shared"}, format="json")
        res = other_client.post(self.url, {"name": "Shared"}, format="json")
        assert res.status_code == 201

    def test_list_scoped_to_owner(self, auth_client, other_client, user, other_user):
        Collection.objects.create(name="A", owner=user)
        Collection.objects.create(name="B", owner=other_user)
        res = auth_client.get(self.url)
        assert res.status_code == 200
        assert [c["name"] for c in res.data["results"]] == ["A"]

    def test_retrieve(self, auth_client, user):
        c = Collection.objects.create(name="C", owner=user)
        res = auth_client.get(reverse("collection-detail", args=[c.id]))
        assert res.status_code == 200
        assert res.data["name"] == "C"

    def test_retrieve_other_forbidden(self, auth_client, other_user):
        c = Collection.objects.create(name="C", owner=other_user)
        res = auth_client.get(reverse("collection-detail", args=[c.id]))
        assert res.status_code == 404

    def test_update(self, auth_client, user):
        c = Collection.objects.create(name="Old", owner=user)
        res = auth_client.patch(
            reverse("collection-detail", args=[c.id]), {"name": "New"}, format="json"
        )
        assert res.status_code == 200
        c.refresh_from_db()
        assert c.name == "New"

    def test_delete(self, auth_client, user):
        c = Collection.objects.create(name="Del", owner=user)
        res = auth_client.delete(reverse("collection-detail", args=[c.id]))
        assert res.status_code == 204
        assert not Collection.objects.filter(id=c.id).exists()

    def test_search(self, auth_client, user):
        Collection.objects.create(name="Alpha", owner=user)
        Collection.objects.create(name="Beta", owner=user)
        res = auth_client.get(self.url, {"search": "Alp"})
        assert res.status_code == 200
        assert [c["name"] for c in res.data["results"]] == ["Alpha"]

    def test_ordering(self, auth_client, user):
        Collection.objects.create(name="Zeta", owner=user)
        Collection.objects.create(name="Alpha", owner=user)
        res = auth_client.get(self.url, {"ordering": "name"})
        assert res.status_code == 200
        assert [c["name"] for c in res.data["results"]] == ["Alpha", "Zeta"]
