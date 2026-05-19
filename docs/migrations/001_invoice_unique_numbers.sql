ALTER TABLE fiscal_invoices
  ADD UNIQUE INDEX uq_fiscal_invoices_number (number);

ALTER TABLE service_invoices
  ADD UNIQUE INDEX uq_service_invoices_number (number);
