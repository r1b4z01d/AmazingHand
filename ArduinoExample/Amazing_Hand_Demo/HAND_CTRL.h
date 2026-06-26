
void Move_Index (float Pos_1, float Pos_2, int Speed)
{
  sc.RegWritePos(1, MiddlePos[0]+Pos_1/Step, 0, Speed);sc.RegWritePos(2, MiddlePos[1]+Pos_2/Step, 0, Speed);sc.RegWriteAction();
}
void Move_Middle (float Pos_1, float Pos_2, int Speed)
{
  sc.RegWritePos(3, MiddlePos[2]+Pos_1/Step, 0, Speed);sc.RegWritePos(4, MiddlePos[3]+Pos_2/Step, 0, Speed);sc.RegWriteAction();
}
void Move_Ring (float Pos_1, float Pos_2, int Speed)
{
  sc.RegWritePos(5, MiddlePos[4]+Pos_1/Step, 0, Speed);sc.RegWritePos(6, MiddlePos[5]+Pos_2/Step, 0, Speed);sc.RegWriteAction();
}
void Move_Thumb (float Pos_1, float Pos_2, int Speed)
{
  sc.RegWritePos(7, MiddlePos[6]+Pos_1/Step, 0, Speed);sc.RegWritePos(8, MiddlePos[7]+Pos_2/Step, 0, Speed);sc.RegWriteAction();
}

void OpenHand()
{  
  red();
  screenUpdate("Opening", 2);
  Move_Index (-35, 35, MaxSpeed);
  Move_Middle (-35, 35, MaxSpeed);
  Move_Ring (-35, 35, MaxSpeed);
  Move_Thumb (-35, 35, MaxSpeed);
  screenUpdate("Opened", 2);
}

void CloseHand()
{
  orange();
  screenUpdate("Closing", 2);
  Move_Index (90, -90, CloseSpeed);
  Move_Middle (90, -90, CloseSpeed);
  Move_Ring (90, -90, CloseSpeed);
  Move_Thumb (70, -70, CloseSpeed+200);
  screenUpdate("Closed", 2);
}

void OpenHand_Progressive()
{
  yellow();
  screenUpdate("OpnProg", 2);     // Opening progressively
  Move_Index (-35, 35, 1200);
  delay(300);
  Move_Middle (-35, 35, 1200);
  delay(300);
  Move_Ring (-35, 35, 1200);
  delay(300);
  Move_Thumb (-35, 35, MaxSpeed);
  screenUpdate("OpenedPg", 2);    // Opened progressive
}

void SpreadHand()
{
  green();
  screenUpdate("Spreading", 2);
  if (Side==1)
  {
    Move_Index (4, 90, MaxSpeed);
    Move_Middle (-32, 32, MaxSpeed);
    Move_Ring (-90, -4, MaxSpeed);
    Move_Thumb (-90, -4, MaxSpeed);  
  } 
  else if (Side==2)
  {
    Move_Index (-60, 0, MaxSpeed);
    Move_Middle (-35, 35, MaxSpeed);
    Move_Ring (-4, 90, MaxSpeed);
    Move_Thumb (-4, 90, MaxSpeed);  
  }
  screenUpdate("Spreaded", 2);
}

void ClenchHand()
{
  springGreen();
  screenUpdate("Clenching", 2);
  if (Side==1)
  {
    Move_Index (-60, 0, MaxSpeed);
    Move_Middle (-35, 35, MaxSpeed);
    Move_Ring (0, 70, MaxSpeed);
    Move_Thumb (-4, 90, MaxSpeed);  
  }
  else if (Side==2)
  {
    Move_Index (0, 60, MaxSpeed);
    Move_Middle (-35, 35, MaxSpeed);
    Move_Ring (-70, 0, MaxSpeed);
    Move_Thumb (-90, -4, MaxSpeed);
  }
  screenUpdate("Clenched", 2);
}

void Index_Pointing()
{
  cyan();
  screenUpdate("Pointing", 2);
  Move_Index (-40, 40, MaxSpeed);
  Move_Middle (90, -90, MaxSpeed);
  Move_Ring (90, -90, MaxSpeed);
  Move_Thumb (90, -90, MaxSpeed);
  screenUpdate("Pointed", 2);
}

void Nonono()
{
  skyBlue();
  Index_Pointing();
  screenUpdate("Wagging", 2);
  for (int i=0;i<3;i++)
  {
    delay(300);
    Move_Index (-10, 80, MaxSpeed);
    delay(300);
    Move_Index (-80, 10, MaxSpeed);
  }
  Move_Index (-35, 35, MaxSpeed);
  delay(400);
  screenUpdate("NoNoNoed", 2);
}

void Perfect()
{
  blue();
  screenUpdate("Perfecting", 2);
  if (Side==1)
  {
    Move_Index (50, -50, MaxSpeed);
    Move_Middle (0, -0, MaxSpeed);
    Move_Ring (-20, 20, MaxSpeed);
    Move_Thumb (65, 12, MaxSpeed);
  }
  else if (Side==2)
  {
    Move_Index (50, -50, MaxSpeed);
    Move_Middle (0, -0, MaxSpeed);
    Move_Ring (-20, 20, MaxSpeed);
    Move_Thumb (-12, -65, MaxSpeed);
  }
  screenUpdate("Perfect", 2);
}

void Victory()
{
  violet();
  screenUpdate("Victory", 2);
  if (Side==1)
  {
    Move_Index (-15, 65, MaxSpeed);
    Move_Middle (-65, 15, MaxSpeed);
    Move_Ring (90, -90, MaxSpeed);
    Move_Thumb (90, -90, MaxSpeed);
  }
  else if (Side==2)
  {
    Move_Index (-65, 15, MaxSpeed);
    Move_Middle (-15, 65, MaxSpeed);
    Move_Ring (90, -90, MaxSpeed);
    Move_Thumb (90, -90, MaxSpeed);
  }
  screenUpdate("Victory", 2);
}

void Pinched()
{
  white();
  screenUpdate("Pinching", 2);
  if (Side==1)
  {
    Move_Index (90, -90, MaxSpeed);
    Move_Middle (90, -90, MaxSpeed);
    Move_Ring (90, -90, MaxSpeed);
    Move_Thumb (0, -75, MaxSpeed);
  }
  else if (Side==2)
  {
    Move_Index (90, -90, MaxSpeed);
    Move_Middle (90, -90, MaxSpeed);
    Move_Ring (90, -90, MaxSpeed);
    Move_Thumb (75, 0, MaxSpeed);
  }
  screenUpdate("Pinched", 2);
}

void Scissors()
{
  magenta();
  screenUpdate("Scissors", 2);
  Victory();
  if (Side==1)
  {
    for (int i=0;i<3;i++)
    {
      delay(300);
      Move_Index (-50, 20, MaxSpeed);
      Move_Middle (-20, 50, MaxSpeed);
      delay(300);
      Move_Index (-15, 65, MaxSpeed);
      Move_Middle (-65, 15, MaxSpeed);
    }  
  }
  else if (Side==2)
  {
    for (int i=0;i<3;i++)
    {
      delay(300);
      Move_Index (-20, 50, MaxSpeed);
      Move_Middle (-50, 20, MaxSpeed);
      delay(300);
      Move_Index (-65, 15, MaxSpeed);
      Move_Middle (-15, 65, MaxSpeed);
    }
  }
  screenUpdate("ScissrEnd", 2);
}

void Fuck()
{
  pink();
  screenUpdate("Flipping", 2);
  if (Side==1)
  {
    Move_Index (90, -90, MaxSpeed);
    Move_Middle (-35, 35, MaxSpeed);
    Move_Ring (90, -90, MaxSpeed);
    Move_Thumb (0, -75, MaxSpeed);
  }
  else if (Side==2)
  {
    Move_Index (90, -90, MaxSpeed);
    Move_Middle (-35, 35, MaxSpeed);
    Move_Ring (90, -90, MaxSpeed);
    Move_Thumb (75, 5, MaxSpeed);
  }
  screenUpdate("Flipped", 2);
}


void parseHandData(char inChar){
  switch (inChar) {
      case '0': {
        OpenHand();
        }
      break;
      case '1' : {
        CloseHand();
        }
      break;
      case '2': {
        OpenHand_Progressive();
        }
      break;
      case '3': {
        SpreadHand();
        }
      break;
      case '4': {
        ClenchHand();
        }
      break;
      case '5': {
        Index_Pointing();
        }
      break;
      case '6': {
        Nonono();
      }
      break;
      case '7': {
        Perfect();
      }
      break;
      case '8': {
        Victory();
      }
      break;
      case '9': {
        Scissors();
      }
      break;
      case 'a': {
        Pinched(); 
      }
      break;
      case 'b': {
        Fuck();
      }
      break;
    }
}

bool isGestureCommand(char c) {
  return (c >= '0' && c <= '9') || c == 'a' || c == 'b';
}

void handleIncomingByte(char c) {
  if (c == '\r') {
    return;
  }
  if (c == '\n') {
    if (jointCommandBuffer.length() > 0) {
      processCommandBuffer(jointCommandBuffer);
      jointCommandBuffer = "";
    }
    return;
  }
  if (jointCommandBuffer.length() == 0 && isGestureCommand(c)) {
    parseHandData(c);
    return;
  }
  if (jointCommandBuffer.length() >= COMMAND_BUFFER_LIMIT) {
    jointCommandBuffer = "";
    return;
  }
  jointCommandBuffer += c;
}

void processCommandBuffer(const String& line) {
  if (line.length() == 0) {
    return;
  }
  if (line.length() == 1 && isGestureCommand(line[0])) {
    parseHandData(line[0]);
    return;
  }
  if (line.startsWith("J:") || line.startsWith("J,")) {
    String payload = line.substring(2);
    if (!parseJointCommand(payload)) {
      WebSerial.println(F("Invalid joint command payload"));
    }
    return;
  }
  WebSerial.println(String(F("Unknown command: ")) + line);
}

bool parseJointCommand(const String& payload) {
  String cleaned = payload;
  cleaned.trim();
  char buffer[COMMAND_BUFFER_LIMIT + 1];
  cleaned.toCharArray(buffer, sizeof(buffer));

  float values[9];
  size_t count = 0;
  char* token = strtok(buffer, ",");
  while (token != nullptr && count < 9) {
    values[count++] = atof(token);
    token = strtok(nullptr, ",");
  }

  if (count < 8) {
    return false;
  }

  int speed = STREAM_DEFAULT_SPEED;
  if (count >= 9) {
    speed = constrain((int)values[8], 50, 2000);
  }

  applyJointTargets(values, 8, speed);
  return true;
}

void applyJointTargets(const float* offsets, size_t count, int speed) {
  int limitedSpeed = constrain(speed, 50, 2000);
  for (size_t i = 0; i < count && i < 8; ++i) {
    float offset = offsets[i];
    int target = MiddlePos[i] + offset / Step;
    target = constrain(target, 0, 1023);
    sc.RegWritePos(i + 1, target, 0, limitedSpeed);
  }
  sc.RegWriteAction();
}
