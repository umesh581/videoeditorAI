/**
 * Constituency Grievance Intake Form — Auto-Generator
 * Google Apps Script (JavaScript)
 *
 * HOW TO RUN (one-time, takes 60 seconds):
 *   1. Go to https://script.google.com → New Project
 *   2. Paste this entire file, replacing the default code
 *   3. Click ▶ Run → select "createGrievanceForm"
 *   4. Approve permissions when prompted
 *   5. Check the Execution Log for your Form URL and Sheet ID
 *   6. Copy those values into .streamlit/secrets.toml
 */

function createGrievanceForm() {

  // ── 1. Create the Form ──────────────────────────────────────────────────────
  var form = FormApp.create('📋 Manikonda–Neknampur Constituency Grievance Report');
  form.setDescription(
    'Report a civic issue in your area. Your submission goes directly to the ' +
    "People's Representative and is tracked until resolution.\n\n" +
    '⏱️ Takes 2 minutes | Available in English & Telugu\n' +
    '📞 For emergencies call 100 (Police) or 1800-425-0019 (GHMC)'
  );
  form.setCollectEmail(false);
  form.setAllowResponseEdits(false);
  form.setLimitOneResponsePerUser(false);
  form.setProgressBar(true);

  // ── 2. Section 1: Who are you? ─────────────────────────────────────────────
  form.addSectionHeaderItem()
    .setTitle('Section 1 of 4 — Reporter Details')
    .setHelpText('Optional. Providing your phone helps us update you on the resolution.');

  form.addTextItem()
    .setTitle('Reporter Name')
    .setRequired(false)
    .setHelpText('Optional — you can submit anonymously');

  form.addTextItem()
    .setTitle('Reporter Phone')
    .setRequired(false)
    .setHelpText('We will SMS you when the issue is resolved');

  // ── 3. Section 2: Where? ───────────────────────────────────────────────────
  form.addSectionHeaderItem()
    .setTitle('Section 2 of 4 — Location')
    .setHelpText('Tell us exactly where the problem is');

  var locationItem = form.addListItem().setTitle('Location').setRequired(true);
  locationItem.setChoiceValues([
    'Manikonda Village',
    'Neknampur',
    'Puppalguda',
    'Lanco Hills',
    'Khajaguda',
    'Nallagandla',
    'Raj Bhavan Colony',
    'Alkapur Township',
    'Fairfield Colony',
    'Lakshmi Nagar Colony',
    'YSR Colony',
    'Byouth Colony',
    'Pioneer Estate',
    'EVV Colony',
    'EIPL Tamarind',
    'Manikonda Basti',
    'Neknampur Layout',
    'Puppalguda Extension',
    'Other (specify below)',
  ]);

  form.addTextItem()
    .setTitle('Custom Location')
    .setRequired(false)
    .setHelpText('Only fill if you selected "Other" above — street name or landmark');

  form.addTextItem()
    .setTitle('Ward Number')
    .setRequired(false)
    .setHelpText('e.g. 127, 128 — check your GHMC voter slip');

  // ── 4. Section 3: What is the problem? ────────────────────────────────────
  form.addSectionHeaderItem()
    .setTitle('Section 3 of 4 — Problem Details')
    .setHelpText('Use the official CPGRAMS grievance categories — same as the government portal');

  var catItem = form.addListItem()
    .setTitle('Grievance Category (CPGRAMS)')
    .setRequired(true)
    .setHelpText('Select the category that best matches your problem');
  catItem.setChoiceValues([
    'Civic amenities / Quality of service',
    'Delay in decision / implementation',
    'Revenue / Land / Tax',
    'Corruption / Malpractices',
    'Service matters (Govt employees)',
    'Law & Order',
    'Harassment / Misbehaviour',
    'Compensations / Refunds',
    'Social Evils',
    'Retirement dues',
    'SC / ST / Backward class issues',
    'Legal Redress',
    'Requests / Permissions',
    'Central Govt miscellaneous',
    'State Govt miscellaneous',
  ]);

  var civicItem = form.addListItem()
    .setTitle('Civic Sub-category')
    .setRequired(false)
    .setHelpText('Only if you selected "Civic amenities" above');
  civicItem.setChoiceValues([
    'Water supply / shortage',
    'Drainage / flooding',
    'Road / pothole',
    'Power cut / electricity',
    'Street lights',
    'Garbage / sanitation',
    'Lake / nala encroachment',
    'Open space encroachment',
    'Tree fall / maintenance',
    'Public toilet',
    'Other civic issue',
  ]);

  form.addParagraphTextItem()
    .setTitle('Issue Description')
    .setRequired(true)
    .setHelpText(
      'Describe the problem in detail:\n' +
      '• How long has this been happening?\n' +
      '• How many households are affected?\n' +
      '• Have you complained before? What happened?\n' +
      '(Minimum 30 characters)'
    );

  form.addTextItem()
    .setTitle('Families Affected')
    .setRequired(false)
    .setHelpText('Approximate number of households impacted — e.g. 50');

  var urgencyItem = form.addListItem()
    .setTitle('Urgency Level')
    .setRequired(true);
  urgencyItem.setChoiceValues([
    'Critical — Immediate risk to health/safety',
    'High — Affecting daily life significantly',
    'Medium — Ongoing inconvenience',
    'Low — Long-standing, can wait',
  ]);

  // ── 5. Section 4: Evidence ─────────────────────────────────────────────────
  form.addSectionHeaderItem()
    .setTitle('Section 4 of 4 — Evidence (Optional)')
    .setHelpText('A photo or video dramatically increases chances of resolution');

  form.addTextItem()
    .setTitle('Photo / Evidence Link')
    .setRequired(false)
    .setHelpText(
      'Upload your photo/video to Google Drive or WhatsApp, then paste the link here.\n' +
      'Tip: Upload to https://drive.google.com → Share → Copy link'
    );

  form.addTextItem()
    .setTitle('Previous Complaint Reference')
    .setRequired(false)
    .setHelpText('If you already filed on CPGRAMS / GHMC 311 / HMWSSB — paste the reference number');

  // ── 6. Confirmation message ────────────────────────────────────────────────
  form.setConfirmationMessage(
    '✅ Your grievance has been recorded!\n\n' +
    "Our team reviews submissions daily. The People's Representative will " +
    'personally follow up on high-priority cases.\n\n' +
    '📱 Share this form with your neighbours:\n' +
    form.shortenFormUrl(form.getPublishedUrl()) + '\n\n' +
    '🙏 Thank you for helping build a better Manikonda–Neknampur.'
  );

  // ── 7. Connect to Google Sheet ────────────────────────────────────────────
  var ss = SpreadsheetApp.create('Constituency Grievances — Manikonda Neknampur');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());

  // ── 8. Format the Sheet ───────────────────────────────────────────────────
  var sheet = ss.getActiveSheet();
  sheet.setName('Grievances');

  // Freeze header row
  sheet.setFrozenRows(1);

  // Auto-resize columns
  sheet.autoResizeColumns(1, 15);

  // Header formatting
  var header = sheet.getRange(1, 1, 1, sheet.getLastColumn());
  header.setBackground('#1E3A5F');
  header.setFontColor('#FFFFFF');
  header.setFontWeight('bold');

  // Add a Status column for the rep to track manually
  sheet.getRange(1, sheet.getLastColumn() + 1).setValue('Status');
  sheet.getRange(1, sheet.getLastColumn() + 1).setValue('Assigned To');
  sheet.getRange(1, sheet.getLastColumn() + 1).setValue('Resolution Notes');
  sheet.getRange(1, sheet.getLastColumn() + 1).setValue('Resolved Date');

  // ── 9. Set up sheet sharing so the dashboard can read it ─────────────────
  // Make the sheet readable by anyone with the link (for API key access)
  ss.setAnonymousAccess(true, false);

  // ── 10. Log results ───────────────────────────────────────────────────────
  Logger.log('');
  Logger.log('══════════════════════════════════════════════');
  Logger.log(' CONSTITUENCY GRIEVANCE FORM CREATED ✅');
  Logger.log('══════════════════════════════════════════════');
  Logger.log('');
  Logger.log('📋 FORM URL (share this with volunteers):');
  Logger.log(form.getPublishedUrl());
  Logger.log('');
  Logger.log('🔗 SHORT URL:');
  Logger.log(form.shortenFormUrl(form.getPublishedUrl()));
  Logger.log('');
  Logger.log('📊 GOOGLE SHEET URL:');
  Logger.log(ss.getUrl());
  Logger.log('');
  Logger.log('🔑 SHEET ID (copy to secrets.toml):');
  Logger.log(ss.getId());
  Logger.log('');
  Logger.log('📌 Add to .streamlit/secrets.toml:');
  Logger.log('[google]');
  Logger.log('sheet_id = "' + ss.getId() + '"');
  Logger.log('api_key  = "YOUR_GOOGLE_API_KEY"');
  Logger.log('');
  Logger.log('See FORM_SETUP guide for API key setup (2 min).');
  Logger.log('══════════════════════════════════════════════');
}
