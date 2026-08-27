"""
Tests for restocking API endpoints.
"""
import pytest


class TestRestockRecommendationsEndpoint:
    """Test suite for GET /api/restocking/recommendations."""

    def test_recommendations_requires_budget_param(self, client):
        """Test that budget is a required query parameter."""
        response = client.get("/api/restocking/recommendations")
        assert response.status_code == 422

    def test_recommendations_rejects_negative_budget(self, client):
        """Test that a negative budget is rejected."""
        response = client.get("/api/restocking/recommendations?budget=-100")
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data

    def test_recommendations_zero_budget_returns_empty(self, client):
        """Test that a zero budget yields no recommendations."""
        response = client.get("/api/restocking/recommendations?budget=0")
        assert response.status_code == 200

        data = response.json()
        assert data["recommendations"] == []
        assert data["total_allocated"] == 0
        assert data["remaining_budget"] == 0

    def test_recommendations_only_increasing_positive_shortfall(self, client):
        """Test that only increasing-trend items with positive shortfall are ever recommended."""
        response = client.get("/api/restocking/recommendations?budget=100000")
        assert response.status_code == 200

        data = response.json()
        skus = {rec["item_sku"] for rec in data["recommendations"]}
        assert skus == {"WDG-001", "GSK-203", "FLT-405"}

        for rec in data["recommendations"]:
            assert rec["trend"] == "increasing"
            assert rec["shortfall"] > 0

    def test_recommendations_priority_order_by_shortfall(self, client):
        """Test that recommendations are ranked by shortfall descending."""
        response = client.get("/api/restocking/recommendations?budget=100000")
        assert response.status_code == 200

        data = response.json()
        ordered_skus = [rec["item_sku"] for rec in data["recommendations"]]
        assert ordered_skus == ["WDG-001", "FLT-405", "GSK-203"]

    def test_recommendations_respect_budget_cap(self, client):
        """Test full/partial fill quantities and totals at a constrained budget."""
        response = client.get("/api/restocking/recommendations?budget=3000")
        assert response.status_code == 200

        data = response.json()
        by_sku = {rec["item_sku"]: rec for rec in data["recommendations"]}

        assert by_sku["WDG-001"]["recommended_quantity"] == 150
        assert by_sku["WDG-001"]["fully_fulfilled"] is True

        assert by_sku["FLT-405"]["recommended_quantity"] == 150
        assert by_sku["FLT-405"]["fully_fulfilled"] is True

        assert by_sku["GSK-203"]["recommended_quantity"] == 18
        assert by_sku["GSK-203"]["fully_fulfilled"] is False

        assert data["total_allocated"] == 2998.5
        assert data["remaining_budget"] == 1.5

    def test_recommendations_partial_fill_math(self, client):
        """Test that a small budget only partially fills the top-priority item."""
        response = client.get("/api/restocking/recommendations?budget=1000")
        assert response.status_code == 200

        data = response.json()
        assert len(data["recommendations"]) == 1

        rec = data["recommendations"][0]
        assert rec["item_sku"] == "WDG-001"
        assert rec["recommended_quantity"] == 80
        assert rec["subtotal"] == 1000.0
        assert rec["fully_fulfilled"] is False
        assert data["remaining_budget"] == 0

    def test_recommendations_budget_too_small_for_any_unit(self, client):
        """Test that a budget smaller than any candidate's unit cost yields nothing."""
        response = client.get("/api/restocking/recommendations?budget=1")
        assert response.status_code == 200

        data = response.json()
        assert data["recommendations"] == []


class TestCreateRestockOrderEndpoint:
    """Test suite for POST /api/restocking/orders."""

    def test_create_restock_order_success(self, client):
        """Test submitting a valid restock order computes prices/lead time server-side."""
        response = client.post(
            "/api/restocking/orders",
            json={
                "budget": 2000,
                "items": [
                    {"item_sku": "WDG-001", "quantity": 50},
                    {"item_sku": "FLT-405", "quantity": 20},
                ],
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["total_cost"] == 755.0
        assert data["lead_time_days"] == 10
        assert data["status"] == "Submitted"
        assert data["budget"] == 2000

        items_by_sku = {item["item_sku"]: item for item in data["items"]}
        assert items_by_sku["WDG-001"]["unit_cost"] == 12.5
        assert items_by_sku["WDG-001"]["subtotal"] == 625.0
        assert items_by_sku["WDG-001"]["item_name"] == "Industrial Widget Type A"
        assert items_by_sku["FLT-405"]["unit_cost"] == 6.5
        assert items_by_sku["FLT-405"]["subtotal"] == 130.0

        assert "T" in data["order_date"]
        assert "T" in data["expected_delivery"]

    def test_create_restock_order_unknown_sku_404(self, client):
        """Test that an unknown item_sku is rejected with 404."""
        response = client.post(
            "/api/restocking/orders",
            json={"budget": 100, "items": [{"item_sku": "FAKE-999", "quantity": 1}]},
        )
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data

    def test_create_restock_order_rejects_zero_quantity(self, client):
        """Test that a zero quantity line item is rejected with 400."""
        response = client.post(
            "/api/restocking/orders",
            json={"budget": 100, "items": [{"item_sku": "WDG-001", "quantity": 0}]},
        )
        assert response.status_code == 400

    def test_create_restock_order_rejects_negative_quantity(self, client):
        """Test that a negative quantity line item is rejected with 400."""
        response = client.post(
            "/api/restocking/orders",
            json={"budget": 100, "items": [{"item_sku": "WDG-001", "quantity": -5}]},
        )
        assert response.status_code == 400

    def test_create_restock_order_rejects_empty_items(self, client):
        """Test that an order with no line items is rejected with 400."""
        response = client.post(
            "/api/restocking/orders",
            json={"budget": 100, "items": []},
        )
        assert response.status_code == 400

    def test_create_restock_order_missing_budget_422(self, client):
        """Test that a missing budget field fails Pydantic validation."""
        response = client.post(
            "/api/restocking/orders",
            json={"items": [{"item_sku": "WDG-001", "quantity": 1}]},
        )
        assert response.status_code == 422

    def test_create_restock_order_missing_items_422(self, client):
        """Test that a missing items field fails Pydantic validation."""
        response = client.post(
            "/api/restocking/orders",
            json={"budget": 100},
        )
        assert response.status_code == 422


class TestGetRestockOrdersEndpoint:
    """Test suite for GET /api/restocking/orders."""

    # restock_orders is a module-level list mutated in place across the whole
    # pytest session (same pattern as purchase_orders), so these tests assert
    # "the order I just created is present/correct" rather than exact list
    # length or emptiness.

    def test_get_restock_orders_returns_list(self, client):
        """Test that the endpoint always returns a list."""
        response = client.get("/api/restocking/orders")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_submitted_order_appears_in_list(self, client):
        """Test that a newly submitted order shows up in the orders list."""
        create_response = client.post(
            "/api/restocking/orders",
            json={"budget": 500, "items": [{"item_sku": "GSK-203", "quantity": 10}]},
        )
        assert create_response.status_code == 200
        created = create_response.json()

        list_response = client.get("/api/restocking/orders")
        assert list_response.status_code == 200

        all_orders = list_response.json()
        match = next((o for o in all_orders if o["id"] == created["id"]), None)
        assert match is not None
        assert match["total_cost"] == created["total_cost"]
        assert match["lead_time_days"] == created["lead_time_days"]
