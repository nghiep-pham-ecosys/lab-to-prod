// Run: java IntegerCache.java   (expected output in IntegerCache.expected)
public class IntegerCache {
    public static void main(String[] args) {
        Integer a = 127, b = 127;
        Integer c = 128, d = 128;
        System.out.println("127 == 127: " + (a == b));
        System.out.println("128 == 128: " + (c == d));
        System.out.println("128 equals 128: " + c.equals(d));
        String s1 = "lab";
        String s2 = new String("lab");
        System.out.println("literal == new String: " + (s1 == s2));
        System.out.println("literal equals new String: " + s1.equals(s2));
    }
}
