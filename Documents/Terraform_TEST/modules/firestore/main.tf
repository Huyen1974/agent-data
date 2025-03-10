resource "google_firestore_database" "firestore_db" {
  project                     = var.project_id
  name                        = var.name  # Dùng biến thay vì hardcode "(default)"
  location_id                 = var.region
  type                        = "FIRESTORE_NATIVE"
  delete_protection_state     = "DELETE_PROTECTION_DISABLED"

  lifecycle {
    prevent_destroy = true
  }
}
