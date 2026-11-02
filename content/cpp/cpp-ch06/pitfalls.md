# cpp-ch06 易错点（Pitfalls）

1. **对象切片（Slicing）：用值传递多态对象**
   把派生对象按**值**赋给基类变量/参数时，只拷贝「基类子对象」，派生部分被切掉，且虚调用不再动态绑定：
   ```cpp
   void f(Animal a) { a.speak(); }   // 永远调 Animal::speak，即便传入 Dog
   Dog d; f(d);                       // d 被切片成 Animal
   ```
   ✅ 多态一律用**引用或指针**（`Animal&` / `Animal*`）传递；容器里存 `Base*` 或 `std::unique_ptr<Base>`。

2. **基类析构函数未声明 `virtual` → 派生部分泄漏 / UB**
   ```cpp
   struct Base { ~Base() {} };        // 非 virtual
   struct Derived : Base { int* p = new int[8]; ~Derived(){ delete[] p; } };
   Base* b = new Derived;
   delete b;                          // 只调 ~Base，~Derived 不执行 → p 泄漏（未定义行为）
   ```
   ✅ 凡是**打算被多态继承**的基类，析构函数一律 `virtual`（C++11 起可 `= default`）。

3. **忘记 `override`：签名写错却「默默新增重载」**
   ```cpp
   struct Base { virtual void foo(int); };
   struct Derived : Base { void foo(double) override; };  // 编译错误：根本没有可覆盖的 foo(double)
   // 若漏写 override：foo(double) 只是一个新函数，foo(int) 仍走基类 —— 多态静默失效
   ```
   ✅ 所有意图覆盖的虚函数都加 `override`，让编译器替你校验签名一致性。

4. **多重继承的菱形二义性**
   ```cpp
   struct A { void f(); };
   struct B : A {}; struct C : A {};
   struct D : B, C {};   // D 里有两份 A 子对象
   D d; d.f();           // 歧义：B::A::f 还是 C::A::f？——编译失败
   ```
   ✅ 用**虚继承** `struct B : virtual A` 让 D 中只有一份 A；或显式 `d.B::f()` 消歧（治标）。

5. **`dynamic_cast` 对非多态类型返回 null / 编译失败**
   - 对**没有虚函数**的类做 `dynamic_cast<Derived*>(base_ptr)`：引用版本编译失败，指针版本**返回 null**（不做运行时检查）。
   - 即便类型匹配，若基类无虚函数，指针 `dynamic_cast` 也会返回 null。
   ```cpp
   struct Base {}; struct Der : Base {};   // 无虚函数 → 非多态
   Base* b = new Der;
   Der* d = dynamic_cast<Der*>(b);          // d == nullptr！（非多态，查表无从谈起）
   ```
   ✅ 需要运行时向下转型的前提是：**基类至少有一个虚函数**（开启 RTTI）。否则请用 `static_cast`（由程序员保证安全）。

6. **基类成员遮蔽（Name Hiding）**
   派生类定义了与基类**同名**的成员/函数，会**隐藏**基类所有同名重载，而非重载：
   ```cpp
   struct Base { void g(int); void g(double); };
   struct Der : Base { void g(int); };       // 隐藏了 Base::g(double)
   Der d; d.g(1.0);                          // 错误：Base::g(double) 被隐藏
   ```
   ✅ 若想保留基类重载，用 `using Base::g;` 引入作用域；或显式 `Base::g(...)`。

7. **在基类构造/析构中调用虚函数不触发多态**
   基类构造期间 vptr 指向「当前构造层的 vtable」，派生部分尚未存在；析构时派生部分已销毁。因此其中的虚调用**静态绑定到当前层**：
   ```cpp
   struct Base { Base(){ virt(); } virtual void virt(){ cout<<"B"; } };
   struct Der : Base { void virt() override { cout<<"D"; } };
   Der d;   // 输出 "B"（构造 Base 时调的是 Base::virt，不是 Der::virt）
   ```
   ✅ 绝不在构造/析构函数里依赖虚函数的多态行为；把多态初始化推迟到构造完成之后。
8. **基类缺虚析构，多态删除泄漏** —— `Base* p = new Der; delete p;` 若 `~Base()` 非虚，只调基类析构，派生部分泄漏。正确写法：任何打算经基类指针释放的类，`virtual ~Base() = default;`。
9. **漏写 `override` 导致「假重写」** —— 签名不符时本意重写却变成新函数，静默成功。正确写法：所有重写加 `override`，编译器替你校验签名。
10. **按值传参触发对象切片** —— `Base b = der;` 只拷基类子对象，派生部分丢失。正确写法：多态类型只用指针/引用（含智能指针）传递。
11. **菱形继承产生两份基类子对象** —— `D : B, C` 而 `B,C : A` 时 `d.x` 歧义。正确写法：需要共享用 `virtual` 继承 `B : virtual A`。
12. **派生类名字遮蔽基类重载** —— 派生写 `f(int)` 会隐藏基类所有 `f(...)`。正确写法：派生里 `using Base::f;` 拉回基类重载集。
13. **纯虚析构未提供定义导致链接错误** —— `virtual ~Base() = 0;` 声明后派生析构会调用它，却无函数体。正确写法：类外补 `Base::~Base() {}`。
14. **`dynamic_cast` 对引用失败抛异常** —— 指针失败返回 null，引用失败抛 `std::bad_cast`。正确写法：引用版本要 `try/catch`，或改用品指针判空。
15. **滥用 RTTI 带来开销与可移植问题** —— `dynamic_cast`/`typeid` 依赖运行期类型信息，`-fno-rtti` 下不可用。正确写法：能用虚函数多态就别用 RTTI，必要时用 `std::variant`+`std::visit`。
