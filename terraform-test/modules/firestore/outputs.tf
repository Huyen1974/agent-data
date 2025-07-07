output "firestore_database_id" {
  value       = google_firestore_database.firestore_db.name
  description = "Tên Firestore DB"
}

output "firestore_database_region" {
  value       = google_firestore_database.firestore_db.location_id
  description = "Region của Firestore DB"
}
