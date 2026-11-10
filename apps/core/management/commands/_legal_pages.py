"""Draft legal pages. Placeholders like [[legal_name]] are filled from Site settings when the page is shown.

These are starting drafts written for a digital-download + consulting business. Have them reviewed by a lawyer.
"""

REVIEW_NOTE = '<p class="legal-note"><em>Last updated: [[updated]]</em></p>'

TERMS = REVIEW_NOTE + """
<p>These Terms of Service ("Terms") govern your use of [[site_url]] (the "Site") and any purchase from [[legal_name]] ("we", "us")[[registration_suffix]]. By using the Site or buying a product you agree to these Terms.</p>
<h2>1. What we sell</h2>
<p>We sell <strong>digital products</strong> (editable document templates, spreadsheets, checklists and toolkits for governance, risk and compliance) delivered by download, and <strong>consulting services</strong> (such as ISMS implementation, IS audit, VAPT, risk management and training) delivered online under a separate proposal or statement of work.</p>
<h2>2. Prices and payment</h2>
<ul>
<li><p>All prices are shown and charged in <strong>US dollars (USD)</strong>. Your bank may apply its own currency conversion or foreign transaction fees.</p></li>
<li><p>Payments are processed securely by <strong>Stripe</strong>. We never see or store your full card details.</p></li>
<li><p>Each product is a one-time purchase. There are no subscriptions or automatic renewals.</p></li>
<li><p>Coupon codes are subject to the conditions shown with them and cannot be exchanged for cash.</p></li>
</ul>
<h2>3. Delivery</h2>
<p>Digital products are available to download immediately after payment. See our <a href="/delivery/">Delivery Policy</a>.</p>
<h2>4. Licence to use the products</h2>
<p>When you buy a product you receive a licence (Single user, Team or Organization) as described in our <a href="/license/">License Terms</a>. We keep all intellectual property rights. You may not resell, share, publish or redistribute the files.</p>
<h2>5. Refunds and cancellations</h2>
<p>See our <a href="/refunds/">Refund &amp; Cancellation Policy</a>.</p>
<h2>6. Accounts</h2>
<p>You can buy without an account. If you sign in to My Library you are responsible for keeping access to your email account secure.</p>
<h2>7. Acceptable use</h2>
<p>You must not misuse the Site, attempt to access it without authorization, interfere with its operation, or use the products for any unlawful purpose.</p>
<h2>8. No legal advice; no guarantee</h2>
<p>Our products and content are professional guidance. They are not legal advice and do not guarantee certification, audit results or regulatory compliance. See our <a href="/disclaimer/">Disclaimer</a>.</p>
<h2>9. Limitation of liability</h2>
<p>To the maximum extent permitted by law, our total liability for any claim relating to a product is limited to the amount you paid for that product, and we are not liable for indirect or consequential losses.</p>
<h2>10. Governing law</h2>
<p>These Terms are governed by the laws of [[governing_law]], without regard to conflict-of-law rules.</p>
<h2>11. Changes</h2>
<p>We may update these Terms. The version in force at the time of your purchase applies to that purchase.</p>
<h2>12. Contact</h2>
<p>[[legal_name]], [[address]]. Email: <a href="mailto:[[email]]">[[email]]</a>[[phone_line]].</p>
"""

PRIVACY = REVIEW_NOTE + """
<p>This Privacy Policy explains how [[legal_name]] ("we", "us") collects and uses personal data when you use [[site_url]]. We are the data controller. Contact: <a href="mailto:[[email]]">[[email]]</a>, [[address]].</p>
<h2>What we collect</h2>
<ul>
<li><p><strong>Orders:</strong> name, email, country, items purchased, license tier, amounts and coupon used. Card payments are handled by Stripe; we receive only the payment status, not your card number.</p></li>
<li><p><strong>Account (My Library):</strong> your email address and sign-in history.</p></li>
<li><p><strong>Contact forms and call bookings:</strong> name, email, company, phone (optional), your message, any file you attach, and the time and timezone you choose.</p></li>
<li><p><strong>Newsletter:</strong> your email address, when and where you signed up, and the IP address used to consent.</p></li>
<li><p><strong>Technical data:</strong> IP address, browser type, the page that referred you, and download logs used to protect paid files.</p></li>
<li><p><strong>Analytics:</strong> only if you accept analytics cookies (see our <a href="/cookies/">Cookie Policy</a>).</p></li>
</ul>
<h2>Why we use it (legal basis)</h2>
<ul>
<li><p>To deliver your purchase, provide downloads and support (performance of a contract).</p></li>
<li><p>To keep accounting and tax records (legal obligation).</p></li>
<li><p>To prevent fraud and abuse and secure paid files (legitimate interests).</p></li>
<li><p>To send the newsletter and use analytics cookies (your consent, which you can withdraw at any time).</p></li>
</ul>
<h2>Who we share it with</h2>
<p>We use trusted service providers who process data on our behalf: Stripe (payments), our hosting provider, Cloudflare (file storage), our email delivery provider, our newsletter tool if you subscribe, and Google Analytics and advertising pixels only if you accept analytics cookies. We do not sell your personal data.</p>
<h2>International transfers</h2>
<p>Some providers may process data outside your country. Where required, transfers are protected by appropriate safeguards such as standard contractual clauses.</p>
<h2>How long we keep it</h2>
<p>Order and invoice records: as long as required by tax law (typically up to 7 years). Download access: for the life of your license. Contact and booking messages: up to 2 years. Newsletter: until you unsubscribe.</p>
<h2>Your rights</h2>
<p>Depending on where you live, you may have the right to access, correct, delete or export your data, object to or restrict processing, and withdraw consent. Email <a href="mailto:[[email]]">[[email]]</a> and we will respond within 30 days. You can also complain to your local data protection authority.</p>
<h2>Security</h2>
<p>We use HTTPS everywhere, private storage for paid files, expiring download links, and two-factor authentication for staff.</p>
<h2>Children</h2>
<p>The Site is intended for businesses and professionals and is not directed at children under 16.</p>
"""

REFUNDS = REVIEW_NOTE + """
<h2>Digital products</h2>
<p>Our products are digital files delivered instantly, so we cannot take them back once downloaded. We will gladly <strong>fix the problem or give a full refund</strong> if, within <strong>14 days</strong> of purchase:</p>
<ul>
<li><p>a file is corrupted or won't open and we can't provide a working copy;</p></li>
<li><p>the product is materially different from its description; or</p></li>
<li><p>you were charged twice for the same product by mistake.</p></li>
</ul>
<p>We may also refund at our discretion if you have not downloaded any file from the order.</p>
<h2>How to request a refund</h2>
<p>Email <a href="mailto:[[email]]">[[email]]</a> with your order number and the reason. We reply within 2 business days. Approved refunds go back to the original payment method through Stripe; your bank usually shows them within <strong>5–10 business days</strong>. Download access ends when a refund is issued.</p>
<h2>Cancellations</h2>
<ul>
<li><p><strong>Orders:</strong> there are no subscriptions. An order cannot be cancelled after payment, but the refund rules above apply.</p></li>
<li><p><strong>Free discovery calls:</strong> cancel any time using the link in your booking email.</p></li>
<li><p><strong>Consulting services:</strong> cancellation and refund terms are set out in your proposal or contract. Unless agreed otherwise, work already delivered is not refundable.</p></li>
</ul>
<h2>Chargebacks</h2>
<p>Please contact us first. We resolve most issues within a day. Opening a payment dispute suspends access to the downloads while it is reviewed.</p>
"""

DELIVERY = REVIEW_NOTE + """
<h2>How products are delivered</h2>
<p>All products are <strong>digital downloads</strong>. Nothing is shipped physically and there are no shipping charges.</p>
<ol>
<li><p>Right after payment, the confirmation page shows a <strong>Download</strong> button for each product.</p></li>
<li><p>We also email the download links to the address you entered at checkout, usually within a few minutes.</p></li>
<li><p>You can download again any time from <a href="/account/login/">My Library</a>: sign in with your purchase email and a one-time link.</p></li>
</ol>
<h2>Download links and limits</h2>
<p>For security, each download link is valid for 24 hours and each file can be downloaded a limited number of times per purchase. Fresh links are always available from My Library.</p>
<h2>File formats</h2>
<p>Editable Microsoft Word (.docx) and Excel (.xlsx) files, PDFs, or a ZIP containing them. The requirements are listed on each product page.</p>
<h2>Updates</h2>
<p>When a new version of a product you bought is released, we email you a link to download it at no extra cost.</p>
<h2>Didn't receive it?</h2>
<p>Check your spam folder, then sign in to My Library. Still stuck? Email <a href="mailto:[[email]]">[[email]]</a> with your order number and we will send your files manually.</p>
<h2>Consulting services</h2>
<p>Consulting is delivered online (video calls, shared documents) according to the timeline in your proposal.</p>
"""

COOKIES = REVIEW_NOTE + """
<p>Cookies are small files stored by your browser. We keep their use to a minimum.</p>
<h2>Essential cookies (always on)</h2>
<ul>
<li><p><strong>sessionid</strong>: keeps your cart and sign-in working.</p></li>
<li><p><strong>csrftoken</strong>: protects forms against cross-site request forgery.</p></li>
<li><p>A browser storage entry remembers your cookie choice.</p></li>
</ul>
<h2>Analytics and marketing cookies (only with your consent)</h2>
<p>If you click <strong>Accept</strong> on the cookie banner, we load Google Analytics and, where configured, advertising pixels (Meta, LinkedIn) to understand how the Site is used and measure our campaigns. Nothing is loaded if you click Reject.</p>
<h2>Changing your choice</h2>
<p>Use the <strong>Cookie settings</strong> link in the footer at any time, or clear cookies in your browser.</p>
<h2>Payments</h2>
<p>Checkout happens on Stripe's secure page, which sets its own cookies for fraud prevention under Stripe's privacy policy.</p>
"""

DISCLAIMER = REVIEW_NOTE + """
<h2>Guidance, not legal advice</h2>
<p>Our templates, toolkits, blog articles and consulting outputs are professional guidance based on practical experience. They are not legal advice. You remain responsible for tailoring them to your organization and for your compliance decisions.</p>
<h2>No guarantee of certification</h2>
<p>Using our products does not guarantee that you will pass an audit, obtain certification, or satisfy a regulator. Outcomes depend on how controls are implemented and evidenced in your organization.</p>
<h2>Standards and trademarks</h2>
<p>ISO, ISO/IEC 27001, ISO/IEC 42001 and other standard names are trademarks of their respective owners. Our products are independent and are <strong>not</strong> affiliated with or endorsed by ISO, IEC, NIST, the PCI Security Standards Council, Bangladesh Bank or any certification body. We do not sell copies of the standards themselves; please obtain them from the official publishers.</p>
<h2>External links</h2>
<p>Links to third-party sites are provided for convenience; we are not responsible for their content.</p>
"""

LICENSE = REVIEW_NOTE + """
<h2>1. What you're buying</h2>
<p>When you buy a product from [[legal_name]] you receive a non-exclusive, non-transferable licence to use and modify the files for your organization's internal purposes. We keep all copyright and other intellectual property rights.</p>
<h2>2. License tiers</h2>
<ul>
<li><p><strong>Single user:</strong> one named individual may use the files.</p></li>
<li><p><strong>Team:</strong> up to 10 users within one organization.</p></li>
<li><p><strong>Organization:</strong> unlimited users within one legal entity (not its parent, subsidiaries or clients).</p></li>
</ul>
<h2>3. Consultants</h2>
<p>Consultants may use the files to deliver work to a client, provided a separate licence is purchased for each client organization that receives the documents.</p>
<h2>4. Not allowed</h2>
<ul>
<li><p>Reselling, sublicensing, sharing or redistributing the files, in original or modified form, as templates or products.</p></li>
<li><p>Publishing the files or substantial parts of them online.</p></li>
<li><p>Removing copyright notices from unmodified files.</p></li>
</ul>
<h2>5. Updates</h2>
<p>Your licence includes free updates to the product you purchased for as long as we maintain it.</p>
<h2>6. No warranty</h2>
<p>The templates are provided as guidance and must be tailored to your organization. See our <a href="/disclaimer/">Disclaimer</a>.</p>
"""

# slug, title, body, footer order
LEGAL_PAGES = [
    ("terms", "Terms of Service", TERMS, 10),
    ("privacy", "Privacy Policy", PRIVACY, 20),
    ("refunds", "Refund & Cancellation Policy", REFUNDS, 30),
    ("delivery", "Delivery Policy", DELIVERY, 40),
    ("license", "License Terms", LICENSE, 50),
    ("cookies", "Cookie Policy", COOKIES, 60),
    ("disclaimer", "Disclaimer", DISCLAIMER, 70),
]
