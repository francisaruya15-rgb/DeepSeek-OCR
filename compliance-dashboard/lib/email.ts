import nodemailer from 'nodemailer';

const transporter = nodemailer.createTransport({
  host: process.env.SMTP_HOST,
  port: parseInt(process.env.SMTP_PORT || '587'),
  secure: false,
  auth: {
    user: process.env.SMTP_USER,
    pass: process.env.SMTP_PASSWORD,
  },
});

export async function sendExpiryReminder(
  to: string,
  companyName: string,
  licenseType: string,
  expirationDate: Date,
  daysUntilExpiry: number
) {
  const subject = `License Expiry Reminder: ${licenseType} - ${companyName}`;
  const html = `
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <h2 style="color: ${daysUntilExpiry <= 7 ? '#dc2626' : daysUntilExpiry <= 15 ? '#f59e0b' : '#16a34a'};">
        License Expiry Notification
      </h2>
      <p>Dear Compliance Officer,</p>
      <p>This is an automated reminder that the following license is approaching its expiration date:</p>
      <div style="background-color: #f3f4f6; padding: 15px; border-radius: 5px; margin: 20px 0;">
        <p><strong>Company:</strong> ${companyName}</p>
        <p><strong>License Type:</strong> ${licenseType}</p>
        <p><strong>Expiration Date:</strong> ${expirationDate.toLocaleDateString()}</p>
        <p><strong>Days Until Expiry:</strong> ${daysUntilExpiry} days</p>
      </div>
      <p style="color: ${daysUntilExpiry <= 7 ? '#dc2626' : '#4b5563'};">
        ${daysUntilExpiry <= 7
          ? 'URGENT: This license expires in 7 days or less. Please take immediate action.'
          : 'Please ensure timely renewal to maintain compliance.'}
      </p>
      <p>Best regards,<br>Compliance Dashboard System</p>
    </div>
  `;

  try {
    await transporter.sendMail({
      from: process.env.SMTP_FROM,
      to,
      subject,
      html,
    });
    return true;
  } catch (error) {
    console.error('Error sending email:', error);
    return false;
  }
}
