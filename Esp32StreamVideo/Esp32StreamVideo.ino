#include <WiFi.h>
#include <SPI.h>
#include <TFT_eSPI.h>

// Cấu hình WiFi
const char* ssid = "tên wifi";          // Thay đổi tên WiFi của bạn
const char* password = "mật khẩu wifi";  // Thay đổi mật khẩu WiFi của bạn

TFT_eSPI tft = TFT_eSPI();

// Cấu hình TCP server
WiFiServer server(8888);
WiFiClient client;

// Kích thước màn hình
#define DISPLAY_WIDTH  240
#define DISPLAY_HEIGHT 240

// Kích thước buffer - mỗi buffer chứa nửa màn hình
#define HALF_SCREEN_HEIGHT (DISPLAY_HEIGHT / 2)  // 120 dòng
#define HALF_SCREEN_BUFFER_SIZE (DISPLAY_WIDTH * DISPLAY_HEIGHT)


// Hai buffer động cho nửa màn hình trên và dưới
uint16_t* topBuffer = NULL;
uint16_t* bottomBuffer = NULL;

// Biến theo dõi trạng thái
bool processingTopHalf = true;  // Bắt đầu với nửa trên
uint32_t frameSize = DISPLAY_WIDTH * DISPLAY_HEIGHT * 2;
uint32_t halfFrameSize = frameSize / 2;
uint32_t bytesReceived = 0;

void setup() {
  // Khởi tạo Serial
  Serial.begin(115200);
  Serial.println("Khởi động ESP32 Streaming Receiver");

  // Cấp phát bộ nhớ cho hai buffer
  topBuffer = (uint16_t*)malloc(HALF_SCREEN_BUFFER_SIZE );
  bottomBuffer = (uint16_t*)malloc(HALF_SCREEN_BUFFER_SIZE);

  if (!topBuffer || !bottomBuffer) {
    Serial.println("Lỗi cấp phát bộ nhớ!");
    while (1) {
      delay(1000);  // Dừng nếu không cấp phát được bộ nhớ
    }
  }

  // Khởi tạo màn hình
  tft.begin();
  tft.setRotation(0);  // Chọn hướng màn hình phù hợp (0-3)
  tft.fillScreen(0x0000);  // Màn hình đen

  // Hiển thị thông báo kết nối
  tft.setTextColor(0xFFFF);
  tft.setTextSize(2);
  tft.setCursor(20, 100);
  tft.println("Dang ket noi WiFi...");

  // Kết nối WiFi
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi đã kết nối");
  Serial.print("Địa chỉ IP: ");
  Serial.println(WiFi.localIP());

  // Hiển thị IP lên màn hình
  tft.fillScreen(0x0000);
  tft.setCursor(10, 80);
  tft.println("WiFi da ket noi");
  tft.setCursor(10, 110);
  tft.print("IP: ");
  tft.println(WiFi.localIP());
  tft.setCursor(10, 140);
  tft.println("Dang cho client...");

  // Khởi động server TCP
  server.begin();
}

void loop() {
  // Kiểm tra client kết nối
  if (!client.connected()) { // khong ket noi
    client = server.available(); // mở cổng chờ
    if (client) {
      Serial.println("Client mới đã kết nối");
      tft.fillScreen(0x0000);
      tft.setCursor(10, 100);
      tft.println("Client da ket noi");
      tft.setCursor(10, 130);
      tft.println("Dang nhan du lieu...");
      //      delay(500);

      // Reset các biến trạng thái
      bytesReceived = 0;
      processingTopHalf = true;
    }
  } else {
    //    Serial.println("Disconnected" );
    // Xử lý dữ liệu từ client đã kết nối
    if (client.available()) {
     
      // Xác định buffer hiện tại và vị trí trên màn hình
      uint16_t* currentBuffer = (bytesReceived < HALF_SCREEN_BUFFER_SIZE) ? topBuffer : bottomBuffer;
      int yStart = (bytesReceived < HALF_SCREEN_BUFFER_SIZE) ? 0 : HALF_SCREEN_BUFFER_SIZE;

      // Đọc dữ liệu vào buffer
      uint8_t* bufferPtr = (uint8_t*)currentBuffer;



      size_t availableBytes = client.available();
 
      size_t toRead ;
      if (bytesReceived < HALF_SCREEN_BUFFER_SIZE) {
        toRead = (HALF_SCREEN_BUFFER_SIZE - bytesReceived) <  availableBytes ? (HALF_SCREEN_BUFFER_SIZE - bytesReceived) : availableBytes;
      } else {
        toRead = (frameSize - bytesReceived) <  availableBytes ? (frameSize - bytesReceived) : availableBytes;
      }
     
//      Serial.print("Read at ");
//      Serial.print( (bytesReceived - yStart));
//          Serial.print(" Ystart  ");
//      Serial.print(  yStart);
//      Serial.print(" buff ");
//      Serial.println(currentBuffer == topBuffer ? 1 :2); 

      size_t actualRead = client.read(bufferPtr + (bytesReceived - yStart), toRead);
      bytesReceived += actualRead;


      // Kiểm tra xem đã nhận đủ dữ liệu cho nửa màn hình chưa


      // Kiểm tra xem đã nhận đủ dữ liệu cho toàn bộ frame chưa
      if (bytesReceived >= frameSize) {
        Serial.println("receive frameSize" );
        // Hiển thị lên màn hình
        // Hiển thị nửa trên của màn hình
        tft.setAddrWindow(0, 0, DISPLAY_WIDTH, 120);
        tft.pushColors(topBuffer, DISPLAY_WIDTH * 120);

        // Hiển thị nửa dưới của màn hình
        tft.setAddrWindow(0, 120, DISPLAY_WIDTH, 120);
        tft.pushColors(bottomBuffer, DISPLAY_WIDTH * 120);
        bytesReceived = 0;  // Bắt đầu frame mới
      }
    }
  }
}
void cleanup() {
  // Giải phóng bộ nhớ khi không cần thiết
  if (topBuffer) {
    free(topBuffer);
    topBuffer = NULL;
  }

  if (bottomBuffer) {
    free(bottomBuffer);
    bottomBuffer = NULL;
  }
}
